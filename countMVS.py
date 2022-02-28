#! /usr/bin/env python
"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import csv
import sys
import time
import socket
import psycopg2
import itertools
import requests
import getpass
import logging
import time

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='/var/log/countMVS.log',
                    filemode='w')

# Determine the major Python version this script is running with (2/3)
python_version = sys.version_info[0]

# This is a hard-coded list of log source type IDs that are considered "not MVS"
# Future versions will be more comprehensive in what to exclude but for now this list is all we need to remove
mvsExclude = [331, 352, 359, 361, 382, 405]

# This is a hard-coded map of sensor protocol type ids to the name
# of the protocol parameter that can be used as a unique identifier
idmap = {
    2: "serverIp",
    7: "url",
    8: "databaseServerHostname",
    9: "deviceAddress",
    15: "remoteHost",
    16: "SERVER_ADDRESS",
    17: "SERVER_ADDRESS",
    18: "SERVER_ADDRESS",
    19: "serverAddress",
    20: "databaseServerHostname",
    21: "SERVER_ADDRESS",
    32: "SERVER_ADDRESS",
    34: "ESXIP",
    37: "databaseServerHostname",
    42: "databaseServerHostname",
    43: "vcloudURL",
    54: "loginUrl",
    55: "databaseServerHostname",
    56: "loginUrl",
    60: "remoteHost",
    63: "remoteHost",
    65: "server",
    67: "databaseServerHostname",
    68: "hostname",
    69: "server",
    74: "tenantUrl",
    75: "apiHostname",
    77: "authorizationServerUrl",
    79: "serverurl",
    83: "endpointURL",
    84: "hostname",
    87: "loginEndPoint",
    90: "authorizationEndPoint"
}


# TODO mark ls as multi domain? add IP to multi domain IP list?
class LogSource:

    def __init__(self, sensordeviceid, hostname, devicename, devicetypeid,
                 spconfig, timestamp_last_seen):
        self.sensordeviceid = sensordeviceid
        self.hostname = hostname
        self.devicename = devicename
        self.domain = []
        self.devicetypeid = devicetypeid
        self.spconfig = spconfig
        self.timestamp_last_seen = timestamp_last_seen
        self.multidomain = False

    def __str__(self):
        return "id = {}\nhostname = {}\ndevicename = {}\ndomain = {}\ndevicetypeid = {}\nspconfig = {}\n" \
               "timestamp_last_seen = {}".format(
            self.sensordeviceid,
            self.hostname,
            self.devicename,
            self.domain,
            self.devicetypeid,
            self.spconfig,
            self.timestamp_last_seen)


# Determine a unique identifier for this log source
def get_machine_identifier(conn, spconfig, hostname):
    # If machine is not a special case as listed above then the default identifier is the hostname
    machineId = hostname

    try:
        idCur = conn.cursor()

        # Use spconfig to retrieve sensorprotocolconfigid,
        spidCommand = "select spid from sensorprotocolconfig where id = {};".format(
            spconfig)
        idCur.execute(spidCommand)

        if idCur.rowcount > 1:
            logging.error(
                "Too many rows returned when retrieving spid for id {}, expected only one row."
                .format(spconfig))
            return -1
        elif idCur.rowcount is 0:
            logging.error(
                "No results found for spid with id {}, unable to retrieve machine identifier."
                .format(spconfig))
            return -1
        elif idCur.rowcount is -1:
            logging.error(
                "Error trying to retrieve spid for id {}, unable to retrieve machine identifier."
                .format(spconfig))
            return -1

        spid = idCur.fetchone()[0]
        logging.debug("Executed sql: {} Retrieved spid = {}".format(
            spidCommand, spid))

        # This log source uses a protocol parameter as its identifier, retrieve name of
        # parameter from idmap then retrieve value from postgres
        if spid in idmap:
            paramName = idmap[spid]
            paramCommand = "select value from sensorprotocolconfigparameters where sensorprotocolconfigid = {} and " \
                           "name = '{}';".format(spconfig, paramName)
            idCur.execute(paramCommand)

            if idCur.rowcount > 1:
                logging.error(
                    "Too many rows returned when retrieving machine identifier for id {} and parameter name {}."
                    .format(spconfig, paramName))
                return -1
            elif idCur.rowcount is 0:
                logging.error(
                    "No results found for machine identifer with id {} and parameter name {}."
                    .format(spconfig, paramName))
                return -1
            elif idCur.rowcount is -1:
                logging.error(
                    "Error trying to retrieve machine identifier for id {} and parameter name {}."
                    .format(spconfig, paramName))
                return -1

            machineId = idCur.fetchone()[0]
            logging.debug("Executed sql: {} Retrieved machineId = {}".format(
                paramCommand, machineId))

            # If value is a url we need to retrieve the hostname/IP to use as identifier
            if "//" in machineId:
                # remove substring before double slash
                tmp = machineId.split("//", 1)[1]
                # remove substring after next slash, if exists
                tmp = tmp.split("/", 1)[0]
                # remove substring after next colon, if exists
                tmp = tmp.split(":", 1)[0]
                if tmp:
                    machineId = tmp

    except Exception as e:
        logging.error('Error retrieving records from the sensordevice table.')
        logging.error(e)
        return -1

    return machineId


# In a system with log sources that have multiple domains we can't just count the number of IPs
# We need to count each separate domain listed under an IP as a separate MVS
def multi_domain_count():
    count = 0
    for ip, lsList in deviceMap.items():
        if ip in multiDomainIPs:
            # Need to build a list of all domains for this IP
            domainList = []
            for ls in lsList:
                if domainList is []:
                    domainList = ls.domain
                else:
                    union = list(set(domainList) | set(ls.domain))
                    domainList = union

            # The number of domains is the number of separate MVS using this IP
            logging.debug("IP {} is associated with {} domains".format(
                ip, len(domainList)))
            for domain in domainList:
                count += 1

                if domain in domainCountMap:
                    domainCountMap[domain] += 1
                else:
                    domainCountMap[domain] = 1

        else:
            # This IP is not associated with multiple domains therefore it counts as one MVS
            count += 1

            # Update domain count for this IP
            ls = lsList[0]
            logging.debug("Domain for IP {} is {}".format(ip, ls.domain))
            domain = ls.domain[0]
            if domain in domainCountMap:
                domainCountMap[domain] += 1
            else:
                domainCountMap[domain] = 1

    return count


def get_multiple_domains(conn, ls):
    domains = []

    jsonHeader = {'Accept': 'application/json'}
    jsonTokenHeader = {'SEC': token, 'Accept': 'application/json'}
    auth = ('admin', password)

    # Call API to start a search for log source's events from the past 24 hours
    searchURL = 'https://{}/api/ariel/searches'.format(consoleIP)
    searchQuery = 'select count(), domainid, logsourceid from events where logsourceid = {} ' \
                  'group by domainid last 24 hours'.format(ls.sensordeviceid)
    searchParams = {'query_expression': searchQuery}

    searchResponse = None

    logging.debug(
        "Attempting to start event search through API with URL: {}".format(
            searchURL))
    try:
        if usePassword:
            searchResponse = requests.post(searchURL,
                                           headers=jsonHeader,
                                           params=searchParams,
                                           auth=auth)
        elif useToken:
            searchResponse = requests.post(searchURL,
                                           headers=jsonTokenHeader,
                                           params=searchParams)
    except Exception as ex:
        logging.debug("Error executing API call {}".format(
            searchResponse.text))
        logging.debug(ex)
        return []

    searchId = ""

    if "search_id" in searchResponse.json():
        searchId = searchResponse.json()["search_id"]
        logging.debug(
            "Initiated event search for log source {}, search id is {}".format(
                ls.sensordeviceid, searchId))

    if searchId is "":
        if searchResponse.status_code == 401:
            unauthStr = "API call returned 401 Unauthorized."
            if "locked out" in searchResponse.text:
                unauthStr += "\nYour host has been locked out due to too many failed login attempts. " \
                          "Please try again later."
            elif usePassword:
                unauthStr += "\nYou have provided the incorrect password. Please rerun the script and try again."
            elif useToken:
                unauthStr += "\nYou have provided the incorrect token. Please rerun the script and try again."
            sys.exit(unauthStr)
        elif not searchResponse.ok:
            errStr = "Error: API returned code {}\n{}".format(
                searchResponse.staus_code, searchResponse.text)
            sys.exit(errStr)

        logging.error(
            "Unable to start a search for log source {}'s events, unable to retrieve "
            "domains for this log source".format(ls.sensordeviceid))
        return []

    # We have successfully started a search for the log source's events, poll searchId until search is complete
    statusURL = 'https://{}/api/ariel/searches/{}'.format(consoleIP, searchId)

    searchComplete = False
    checks = 1
    while checks < 60:
        logging.debug(
            "Check if search is complete with URL {}".format(statusURL))
        logging.debug("Attempt {}".format(checks))
        statusResponse = None

        try:
            if usePassword:
                statusResponse = requests.get(statusURL,
                                              headers=jsonHeader,
                                              auth=auth).json()
            elif useToken:
                statusResponse = requests.get(statusURL,
                                              headers=jsonTokenHeader).json()

            logging.debug("Search status is {}".format(
                statusResponse["status"]))
            if statusResponse["status"] == "COMPLETED":
                logging.debug(
                    "Event search is complete for log source {}".format(
                        ls.sensordeviceid))
                searchComplete = True
                break

        except Exception as e:
            logging.error("Error executing API call {}".format(statusResponse))
            logging.error(e)

        checks += 1
        time.sleep(1)

    if not searchComplete:
        logging.error(
            "Event search for log source {} took over 60 seconds to complete, unable to retrieve"
            "domains for this log source".format(ls.sensordeviceid))
        return []

    # Search is complete, iterate through results to build list of domains
    jsonRangeHeader = {'Range': 'items=0-49', 'Accept': 'application/json'}
    jsonRangeTokenHeader = {
        'SEC': token,
        'Range': 'items=0-49',
        'Accept': 'application/json'
    }

    eventsURL = 'https://{}/api/ariel/searches/{}/results'.format(
        consoleIP, searchId)

    eventsResponse = None
    eventsResultList = None

    logging.debug("Check search results with URL {}".format(eventsURL))
    try:
        if usePassword:
            eventsResponse = requests.get(eventsURL,
                                          headers=jsonRangeHeader,
                                          auth=auth)
            eventsResultList = eventsResponse.json()
            logging.debug("results: {}".format(eventsResponse.text))
        elif useToken:
            eventsResponse = requests.get(eventsURL,
                                          headers=jsonRangeTokenHeader)
            eventsResultList = eventsResponse.json()
    except Exception as e:
        logging.error(
            "Error retrieving results for events search for log source {}".
            format(ls.sensordeviceid))
        logging.error(e)
        return []

    if not eventsResponse.ok:
        logging.error("API call was unsuccessful: {}".format(
            eventsResponse.text))
        logging.error("Couldn't retrieve domains for log source {}".format(
            ls.sensordeviceid))
        return []

    logging.debug(
        "API call was successful to retrieve event search results for log source {}"
        .format(ls.sensordeviceid))
    for jsonData in eventsResultList["events"]:
        if "domainid" in jsonData:
            domainId = jsonData["domainid"]
            logging.debug("Found domainid {} for log source {}".format(
                domainId, ls.sensordeviceid))
            try:
                domNameCur = conn.cursor()
                domNameCommand = 'select name from domains where id = {};'.format(
                    domainId)
                domNameCur.execute(domNameCommand)

                if domNameCur.rowcount is 1:
                    domainName = domNameCur.fetchone()[0]
                    if domainName is "None" or domainId == 0:
                        domainName = "Default"

                    logging.debug("Domain id {} is for domain {}".format(
                        domainId, domainName))
                    domains.append(domainName)
                else:
                    logging.error(
                        'Error retrieving domain name for id {}.'.format(
                            domainId))
                    domains.append(domainId)

            except Exception as e:
                logging.error(
                    'Error retrieving domain name for id {}.'.format(domainId))
                logging.error(e)
                domains.append(domainId)

    return domains


# Set a log source's domain if it is only associated with one domain
# if a log source has multiple domains, will set domain to a list of domains
# and will set that log source's mutlidomain flag to true
def set_domain(conn, ls):
    try:
        domainCur = conn.cursor()
        domainCommand = "select b.name from domain_mapping a join domains b on a.domain_id = b.id " \
                        "where a.source_type = 2 and source_id = {};".format(ls.sensordeviceid)
        domainCur.execute(domainCommand)

        if domainCur.rowcount is -1:
            logging.error(
                "Error trying to retrieve domain for log source {}.".format(
                    ls.sensordeviceid))
            return
        elif domainCur.rowcount is 0:
            if multidomain:
                # Log source may be associated with multiple domains
                logging.debug("Log source {} may have multiple domains".format(
                    ls.sensordeviceid))
                multiDomainList = get_multiple_domains(conn, ls)
                ls.domain = multiDomainList

                # Sanity check that LS does in fact have multiple domains
                if len(multiDomainList) >= 1:
                    ls.multidomain = True

            if ls.multidomain is False:
                ls.domain.append("Default")

        elif domainCur.rowcount is 1:
            # Only one row returned, this log source is only associated with one domain
            logging.debug("Log source {} has one domain".format(
                ls.sensordeviceid))
            domain = domainCur.fetchone()[0]
            ls.domain.append(domain)
            logging.debug("Domain for Log source {} was set to {}".format(
                ls.sensordeviceid, domain))

    except Exception as e:
        logging.error('Error retrieving domain for log source {}'.format(
            ls.sensordeviceid))
        logging.error(e)
        return


deviceMap = {}
lsCount = 0
multidomain = False
consoleIP = ""
usePassword = False
password = ""
useToken = False
token = ""
multiDomainIPs = []
domainCountMap = {}

# Compile a list of machines that have received events in the last 24 hours and their log sources
try:
    conn = psycopg2.connect("dbname='qradar' user='qradar'")
except Exception as e:
    sys.exit('Unable to connect to the database')

try:
    cur = conn.cursor()

    # Check if we're on a system with multiple domains
    cur.execute("select count(id) from domains;")
    domainCount = int(cur.fetchone()[0])

    if domainCount > 1:
        multidomain = True
        logging.debug("Count of domains is {}".format(domainCount))
        logging.debug("Multi-Domain system = {}".format(multidomain))

        # If we're on a multi-domain system we may need the console IP to hit the ariel API
        with open("/opt/qradar/conf/nva.hostcontext.conf") as confFile:
            for line in confFile:
                if line.startswith("CONSOLE_PRIVATE_IP="):
                    consoleIP = line.split("=", 1)[1].rstrip()
                    logging.debug("Console IP is {}".format(consoleIP))
        if consoleIP is "":
            # log error but continue executing, it's possible we won't need to hit the API
            logging.error(
                "Unable to retrieve Console IP, we will be unable to make API calls."
            )

        # Prompt user for password/token in case we need to make API calls
        print(
            "This script may need to call the Ariel API to count the MVS across multiple domains.\n"
            "Which authentication would you like to use:\n\t1: Admin User\n\t2: Authorized Service\n\n"
            "(q to quit)\n")
        while True:
            authChoice = None
            if python_version < 3:
                authChoice = raw_input()
            else:
                authChoice = input()
            if authChoice is '1':
                usePassword = True
                password = getpass.getpass(
                    "Please input the Admin user password:\n\n")
                break
            elif authChoice is '2':
                useToken = True
                token = getpass.getpass(
                    "Please input the security token for your Authorized Service:\n\n"
                )
                break
            elif str(authChoice) is 'q' or str(authChoice) is 'Q':
                sys.exit()
            else:
                print(
                    "\nInvalid selection. Please choose from the following options:"
                    "\n\t1. Admin User\n\t2. Authorized Service\n\t(q to quit)\n"
                )
    print("Executing...")

    yesterday = int(round(time.time() * 1000)) - 86400000
    logging.debug("Timestamp for 24 hours ago is {}".format(yesterday))

    cur.execute(
        "select id, hostname, devicename, devicetypeid, spconfig, timestamp_last_seen from sensordevice"
        " where timestamp_last_seen > {} and spconfig is not null;".format(
            yesterday))

    for row in cur.fetchall():
        lsCount += 1

        # If we know this log source does not make the machine an MVS then we can ignore it
        logging.debug("devicetypeid is {}".format(row[3]))
        if row[3] in mvsExclude:
            logging.debug("devicetypeid {} is in mvsExclude".format(row[3]))
            continue

        device = LogSource(row[0], row[1], row[2], row[3], row[4], row[5])
        set_domain(conn, device)

        # Retrieve identifier for the machine this log source is running on
        machine = get_machine_identifier(conn, device.spconfig,
                                         device.hostname)

        # If we can't retrieve a machine ID then skip this device
        if machine is -1:
            logging.error(
                "Couldn't retrieve machine identifier for sensordevice with id {},"
                " fall back to using Log Source Identifier".format(row[0]))
            machine = device.hostname

        # If this log source has multiple domains then keep track of this IP as it will
        # require extra processing during the count
        if device.multidomain:
            multiDomainIPs.append(machine)

        if machine in deviceMap:
            # If machine is already listed, then append this device to its LS list
            deviceMap[machine].append(device)
            logging.debug(
                "Machine {} in the map, adding device with id {} to its list".
                format(machine, device.sensordeviceid))
        else:
            # If machine is not listed then add it to the map
            deviceMap[machine] = [device]

    conn.commit()
    conn.close()

except Exception as e:
    print(e)
    sys.exit('Error retrieving records from the sensordevice table.')

# Machine identifiers are either IPs or hostnames
# Now resolve hostnames to IPs and consolidate any duplicate entries
toAdd = {}
toRemove = []
for identifier in deviceMap:
    try:
        # Will return IP whether identifier is IP or hostname
        ip = socket.gethostbyname(identifier)
    except Exception as e:
        logging.error(e)
        logging.error(
            "Unable to to resolve hostname {} to IP".format(identifier))
        continue

    # If identifier was a hostname that was resolved to an IP
    if ip != identifier:
        logging.debug("hostname {} resolved to IP {}".format(identifier, ip))
        if ip in deviceMap:
            # If this IP is already in the map then consolidate lists
            deviceMap[ip].extend(deviceMap[identifier])
            logging.debug(
                "IP {} is in the map, consolidating lists".format(ip))
        else:
            # If this IP is not already in the map then add it
            toAdd[ip] = deviceMap[identifier]
            logging.debug("IP {} is not in the map, adding".format(ip))

        # Mark the hostname's entry for deletion
        toRemove.append(identifier)

        # Need to also update our list of multiDomainIPs to remove hostnames
        # And add IP to list if it's not already present
        if ip not in multiDomainIPs:
            multiDomainIPs.append(ip)
        if identifier in multiDomainIPs:
            multiDomainIPs.remove(identifier)

# Add entries for IPs that were not already in the map
deviceMap.update(toAdd)

# Remove entries for hostnames that were mapped to IPs
for i in toRemove:
    del deviceMap[i]
    logging.debug(
        "Removing entry for hostname {}, which has been resolved to an IP".
        format(i))

# Hostnames resolved, duplicates removed, now output count and list file
with open('mvsCount.csv', 'w') as output:
    writer = csv.writer(output)
    writer.writerow(deviceMap.keys())
    if python_version < 3:
        writer.writerows(itertools.izip_longest(*deviceMap.values()))
    else:
        writer.writerows(itertools.zip_longest(*deviceMap.values()))

if multidomain:
    mvsCount = multi_domain_count()
else:
    mvsCount = len(deviceMap)

print("\nMVS count for the deployment is {}".format(mvsCount))
if multidomain:
    domainList = list(domainCountMap.keys())
    domainList.sort()
    for dom in domainList:
        print("MVS count for domain {} is {}".format(dom, domainCountMap[dom]))

logging.debug("Total log sources considered = {}".format(lsCount))
