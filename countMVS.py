#! /usr/bin/env python
"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import csv
import getpass
import logging
import socket
import subprocess
import sys
import time
import psycopg2
import requests
import six
import urllib3

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='/var/log/countMVS.log',
                    filemode='w')

# Disable insecure HTTPS warnings as most customers do not have certificate validation correctly configured for consoles
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# This is a hard-coded list of log source type IDs that are considered "not MVS"
# Future versions will be more comprehensive in what to exclude but for now this list is all we need to remove
LOG_SOURCE_EXCLUDE = [331, 352, 359, 361, 382, 405]

# This is a hard-coded map of sensor protocol type ids to the name
# of the protocol parameter that can be used as a unique identifier
SENSOR_PROTOCOL_MAP = {
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
    90: "authorizationEndPoint",
}


# TBD: mark log source as multi domain? add IP to multi domain IP list?
class LogSource:

    # pylint: disable=too-many-instance-attributes, too-many-arguments
    def __init__(self, sensordeviceid, hostname, devicename, devicetypeid, spconfig, timestamp_last_seen):
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
def get_machine_identifier(db_conn, spconfig, hostname):
    # pylint: disable=too-many-return-statements
    # If machine is not a special case as listed above then the default identifier is the hostname
    machine_id = hostname

    try:
        id_cursor = db_conn.cursor()

        # Use spconfig to retrieve sensorprotocolconfigid,
        spid_command = "select spid from sensorprotocolconfig where id = {};".format(spconfig)
        id_cursor.execute(spid_command)

        if id_cursor.rowcount > 1:
            logging.error(
                "Too many rows returned when retrieving spid for id {}, expected only one row.".format(spconfig))
            return -1
        if id_cursor.rowcount == 0:
            logging.error(
                "No results found for spid with id {}, unable to retrieve machine identifier.".format(spconfig))
            return -1
        if id_cursor.rowcount == -1:
            logging.error(
                "Error trying to retrieve spid for id {}, unable to retrieve machine identifier.".format(spconfig))
            return -1

        spid = id_cursor.fetchone()[0]
        logging.debug("Executed sql: {} Retrieved spid = {}".format(spid_command, spid))

        # This log source uses a protocol parameter as its identifier, retrieve name of
        # parameter from SENSOR_PROTOCOL_MAP then retrieve value from postgres
        if spid in SENSOR_PROTOCOL_MAP:
            param_name = SENSOR_PROTOCOL_MAP[spid]
            param_command = "select value from sensorprotocolconfigparameters where sensorprotocolconfigid = {} and " \
                           "name = '{}';".format(spconfig, param_name)
            id_cursor.execute(param_command)

            if id_cursor.rowcount > 1:
                logging.error(
                    "Too many rows returned when retrieving machine identifier for id {} and parameter name {}.".
                    format(spconfig, param_name))
                return -1
            if id_cursor.rowcount == 0:
                logging.error("No results found for machine identifer with id {} and parameter name {}.".format(
                    spconfig, param_name))
                return -1
            if id_cursor.rowcount == -1:
                logging.error("Error trying to retrieve machine identifier for id {} and parameter name {}.".format(
                    spconfig, param_name))
                return -1

            machine_id = id_cursor.fetchone()[0]
            logging.debug("Executed sql: {} Retrieved machine_id = {}".format(param_command, machine_id))

            # If value is a url we need to retrieve the hostname/IP to use as identifier
            if "//" in machine_id:
                # remove substring before double slash
                tmp = machine_id.split("//", 1)[1]
                # remove substring after next slash, if exists
                tmp = tmp.split("/", 1)[0]
                # remove substring after next colon, if exists
                tmp = tmp.split(":", 1)[0]
                if tmp:
                    machine_id = tmp

    except Exception as machine_id_error:
        logging.error('Error retrieving records from the sensordevice table.')
        logging.error(machine_id_error)
        return -1

    return machine_id


# In a system with log sources that have multiple domains we can't just count the number of IPs
# We need to count each separate domain listed under an IP as a separate MVS
def multi_domain_count():
    count = 0
    for ip_address, log_source_list in device_map.items():
        if ip_address in multidomain_ip_list:
            # Need to build a list of all domains for this IP
            domains = []
            for log_source in log_source_list:
                if not domains:
                    domains = log_source.domain
                else:
                    union = list(set(domains) | set(log_source.domain))
                    domains = union

            # The number of domains is the number of separate MVS using this IP
            logging.debug("IP {} is associated with {} domains".format(ip_address, len(domains)))
            for domain in domains:
                count += 1

                if domain in domain_count_map:
                    domain_count_map[domain] += 1
                else:
                    domain_count_map[domain] = 1

        else:
            # This IP is not associated with multiple domains therefore it counts as one MVS
            count += 1

            # Update domain count for this IP
            log_source = log_source_list[0]
            logging.debug("Domain for IP {} is {}".format(ip_address, log_source.domain))
            domain = log_source.domain[0]
            if domain in domain_count_map:
                domain_count_map[domain] += 1
            else:
                domain_count_map[domain] = 1

    return count


def get_multiple_domains(db_conn, log_source):
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    domains = []

    # Call API to start a search for log source's events from the past 24 hours
    search_url = 'https://{}/api/ariel/searches'.format(console_ip)
    search_query = 'select count(), domainid, logsourceid from events where logsourceid = {} ' \
                  'group by domainid last 24 hours'.format(log_source.sensordeviceid)
    search_params = {'query_expression': search_query}

    search_response = None

    logging.debug("Attempting to start event search through API with URL: {}".format(search_url))
    try:
        if use_password:
            search_response = requests.post(search_url,
                                            headers=JSON_HEADER,
                                            params=search_params,
                                            auth=auth,
                                            verify=False)
        elif use_token:
            search_response = requests.post(search_url, headers=json_token_header, params=search_params, verify=False)
    except Exception as ex:
        logging.debug("Error executing API call {}".format(search_response.text))
        logging.debug(ex)
        return []

    search_id = None

    if "search_id" in search_response.json():
        search_id = search_response.json()["search_id"]
        logging.debug("Initiated event search for log source {}, search id is {}".format(
            log_source.sensordeviceid, search_id))

    if not search_id:
        if not search_response.ok:
            sys.exit("Error: API returned code {}\n{}".format(search_response.staus_code, search_response.text))

        logging.error("Unable to start a search for log source {}'s events, unable to retrieve "
                      "domains for this log source".format(log_source.sensordeviceid))
        return []

    # We have successfully started a search for the log source's events, poll search_id until search is complete
    status_url = 'https://{}/api/ariel/searches/{}'.format(console_ip, search_id)

    search_complete = False
    checks = 1
    while checks < 60:
        logging.debug("Check if search is complete with URL {}".format(status_url))
        logging.debug("Attempt {}".format(checks))
        status_response = None

        try:
            if use_password:
                status_response = requests.get(status_url, headers=JSON_HEADER, auth=auth, verify=False).json()
            elif use_token:
                status_response = requests.get(status_url, headers=json_token_header, verify=False).json()

            logging.debug("Search status is {}".format(status_response["status"]))
            if status_response["status"] == "COMPLETED":
                logging.debug("Event search is complete for log source {}".format(log_source.sensordeviceid))
                search_complete = True
                break

        except Exception as status_error:
            if status_response:
                logging.error("Error executing API call {}".format(status_response))
            else:
                logging.error("Error executing API call blank status_response")
            logging.error(status_error)

        checks += 1
        time.sleep(1)

    if not search_complete:
        logging.error("Event search for log source {} took over 60 seconds to complete, unable to retrieve"
                      "domains for this log source".format(log_source.sensordeviceid))
        return []

    # Search is complete, iterate through results to build list of domains
    json_range_header = {'Range': 'items=0-49', 'Accept': 'application/json'}
    json_range_token_header = {'SEC': token, 'Range': 'items=0-49', 'Accept': 'application/json'}

    events_url = 'https://{}/api/ariel/searches/{}/results'.format(console_ip, search_id)

    events_response = None
    events_result_list = None

    logging.debug("Check search results with URL {}".format(events_url))
    try:
        if use_password:
            events_response = requests.get(events_url, headers=json_range_header, auth=auth, verify=False)
            events_result_list = events_response.json()
            logging.debug("results: {}".format(events_response.text))
        elif use_token:
            events_response = requests.get(events_url, headers=json_range_token_header, verify=False)
            events_result_list = events_response.json()
    except Exception as events_error:
        logging.error("Error retrieving results for events search for log source {}".format(log_source.sensordeviceid))
        logging.error(events_error)
        return []

    if not events_response.ok:
        logging.error("API call was unsuccessful: {}".format(events_response.text))
        logging.error("Couldn't retrieve domains for log source {}".format(log_source.sensordeviceid))
        return []

    logging.debug("API call was successful to retrieve event search results for log source {}".format(
        log_source.sensordeviceid))
    for json_data in events_result_list["events"]:
        if "domainid" in json_data:
            domain_id = json_data["domainid"]
            logging.debug("Found domainid {} for log source {}".format(domain_id, log_source.sensordeviceid))
            try:
                domain_name_cursor = db_conn.cursor()
                domain_name_command = 'select name from domains where id = {};'.format(domain_id)
                domain_name_cursor.execute(domain_name_command)

                if domain_name_cursor.rowcount == 1:
                    domain_name = domain_name_cursor.fetchone()[0]
                    if domain_name == "None" or domain_id == 0:
                        domain_name = "Default"

                    logging.debug("Domain id {} is for domain {}".format(domain_id, domain_name))
                    domains.append(domain_name)
                else:
                    logging.error('Error retrieving domain name for id {}.'.format(domain_id))
                    domains.append(domain_id)

            except Exception as domain_error:
                logging.error('Error retrieving domain name for id {}.'.format(domain_id))
                logging.error(domain_error)
                domains.append(domain_id)

    return domains


# Set a log source's domain if it is only associated with one domain
# if a log source has multiple domains, will set domain to a list of domains
# and will set that log source's mutlidomain flag to true
def set_domain(db_conn, log_source):
    try:
        domain_cursor = db_conn.cursor()
        domain_command = "select b.name from domain_mapping a join domains b on a.domain_id = b.id " \
                        "where a.source_type = 2 and source_id = {};".format(log_source.sensordeviceid)
        domain_cursor.execute(domain_command)

        if domain_cursor.rowcount == -1:
            logging.error("Error trying to retrieve domain for log source {}.".format(log_source.sensordeviceid))
            return
        if domain_cursor.rowcount == 0:
            if multidomain:
                # Log source may be associated with multiple domains
                logging.debug("Log source {} may have multiple domains".format(log_source.sensordeviceid))
                multidomain_list = get_multiple_domains(db_conn, log_source)
                log_source.domain = multidomain_list

                # Sanity check that LS does in fact have multiple domains
                if len(multidomain_list) >= 1:
                    log_source.multidomain = True

            if log_source.multidomain is False:
                log_source.domain.append("Default")

        elif domain_cursor.rowcount == 1:
            # Only one row returned, this log source is only associated with one domain
            logging.debug("Log source {} has one domain".format(log_source.sensordeviceid))
            domain = domain_cursor.fetchone()[0]
            log_source.domain.append(domain)
            logging.debug("Domain for Log source {} was set to {}".format(log_source.sensordeviceid, domain))

    except Exception as domain_error:
        logging.error('Error retrieving domain for log source {}'.format(log_source.sensordeviceid))
        logging.error(domain_error)
        return


def is_console():
    try:
        # Can't use popen with resource management in Python 2. If this becomes a Python 3-only script
        # then rewrite using with, and remove the disable rule.
        # Also, for Python 3, using subprocess.run instead of subprocess.Popen is recommended.
        # pylint: disable=consider-using-with
        proc = subprocess.Popen(['/opt/qradar/bin/myver', '-c'], stdout=subprocess.PIPE)
        stdout, _ = proc.communicate()
        return stdout.decode('utf-8').rstrip() == 'true'
    except Exception:
        sys.exit("Unable to determine if host is the console. Exiting.")


if not is_console():
    sys.exit('Running on host that is not console. Exiting.')

JSON_HEADER = {'Accept': 'application/json'}

# The rest of this module is in global scope. The block of variables below plus other individual lines
# have the invalid-name rule disabled because pylint assumes these variables are global constants.
# Ideally the whole module should be refactored as a class to remove any globals.

# pylint: disable=invalid-name
log_source_count = 0
multidomain = False
console_ip = ""
use_password = False
password = ""
use_token = False
token = ""
# pylint: enable=invalid-name

device_map = {}
json_token_header = {}
multidomain_ip_list = []
domain_count_map = {}

# Compile a list of machines that have received events in the last 24 hours and their log sources
try:
    db_connection = psycopg2.connect("dbname='qradar' user='qradar'")
except Exception:
    sys.exit('Unable to connect to the database')

try:
    db_cursor = db_connection.cursor()

    # Check if we're on a system with multiple domains
    db_cursor.execute("select count(id) from domains;")
    domain_count = int(db_cursor.fetchone()[0])

    if domain_count > 1:
        multidomain = True  # pylint: disable=invalid-name
        logging.debug("Count of domains is {}".format(domain_count))
        logging.debug("Multi-Domain system = {}".format(multidomain))

        # If we're on a multi-domain system we may need the console IP to hit the ariel API
        with open("/opt/qradar/conf/nva.hostcontext.conf") as conf_file:  # pylint: disable=unspecified-encoding
            for line in conf_file:
                if line.startswith("CONSOLE_PRIVATE_IP="):
                    console_ip = line.split("=", 1)[1].rstrip()
                    logging.debug("Console IP is {}".format(console_ip))
        if not console_ip:
            # log error but continue executing, it's possible we won't need to hit the API
            logging.error("Unable to retrieve Console IP, we will be unable to make API calls.")

        # Prompt user for password/token in case we need to make API calls
        print("This script may need to call the Ariel API to count the MVS across multiple domains.\n"
              "Which authentication would you like to use:\n\t1: Admin User\n\t2: Authorized Service\n\n"
              "(q to quit)\n")
        while True:
            auth_choice = str(six.moves.input())  # pylint: disable=invalid-name
            if auth_choice == '1':
                use_password = True  # pylint: disable=invalid-name
                password = getpass.getpass("Please input the Admin user password:\n\n")
                auth = ('admin', password)
                break
            if auth_choice == '2':
                use_token = True  # pylint: disable=invalid-name
                token = getpass.getpass("Please input the security token for your Authorized Service:\n\n")
                json_token_header = {'SEC': token, 'Accept': 'application/json'}
                break
            if auth_choice in ('q', 'Q'):
                sys.exit()
            print("\nInvalid selection. Please choose from the following options:"
                  "\n\t1. Admin User\n\t2. Authorized Service\n\t(q to quit)\n")

        print("Checking API connectivity")

        # Call API to start a search for log source's events from the past 24 hours
        check_url = 'https://{}/api/system/about'.format(console_ip)  # pylint: disable=invalid-name

        api_response = None  # pylint: disable=invalid-name

        logging.debug("Attempting to check API with URL: {}".format(check_url))
        try:
            if use_password:
                api_response = requests.get(check_url, headers=JSON_HEADER, auth=auth, verify=False)
            elif use_token:
                api_response = requests.get(check_url, headers=json_token_header, verify=False)
            if api_response.status_code == 401:
                unauth_msg = "API call returned 401 Unauthorized."  # pylint: disable=invalid-name
                if "locked out" in api_response.text:
                    unauth_msg += "\nYour host has been locked out due to too many failed login attempts. " \
                        "Please try again later."
                elif use_password:
                    unauth_msg += "\nYou have provided the incorrect password. Please rerun the script and try again."
                elif use_token:
                    unauth_msg += "\nYou have provided the incorrect token. Please rerun the script and try again."
                sys.exit(unauth_msg)
        except Exception as api_error:
            if api_response.text:
                logging.debug("Error executing API call {}".format(api_response.text))
            else:
                logging.debug("Error executing API call empty api_response.text")
            logging.debug(api_error)
            sys.exit("Error connecting to API")

        print("API Connected Successfully")

    yesterday = int(round(time.time() * 1000)) - 86400000
    logging.debug("Timestamp for 24 hours ago is {}".format(yesterday))

    db_cursor.execute("select id, hostname, devicename, devicetypeid, spconfig, timestamp_last_seen from sensordevice"
                      " where timestamp_last_seen > {} and spconfig is not null;".format(yesterday))

    for row in db_cursor.fetchall():
        log_source_count += 1

        # If we know this log source does not make the machine an MVS then we can ignore it
        logging.debug("devicetypeid is {}".format(row[3]))
        if row[3] in LOG_SOURCE_EXCLUDE:
            logging.debug("devicetypeid {} is in LOG_SOURCE_EXCLUDE".format(row[3]))
            continue

        device = LogSource(row[0], row[1], row[2], row[3], row[4], row[5])
        set_domain(db_connection, device)

        # Retrieve identifier for the machine this log source is running on
        machine = get_machine_identifier(db_connection, device.spconfig, device.hostname)

        # If we can't retrieve a machine ID then skip this device
        if machine == -1:
            logging.error("Couldn't retrieve machine identifier for sensordevice with id {},"
                          " fall back to using Log Source Identifier".format(row[0]))
            machine = device.hostname

        # If this log source has multiple domains then keep track of this IP as it will
        # require extra processing during the count
        if device.multidomain:
            multidomain_ip_list.append(machine)

        if machine in device_map:
            # If machine is already listed, then append this device to its LS list
            device_map[machine].append(device)
            logging.debug("Machine {} in the map, adding device with id {} to its list".format(
                machine, device.sensordeviceid))
        else:
            # If machine is not listed then add it to the map
            device_map[machine] = [device]

    db_connection.commit()
    db_connection.close()

except Exception as sd_error:
    print(sd_error)
    sys.exit('Error retrieving records from the sensordevice table.')

# Machine identifiers are either IPs or hostnames
# Now resolve hostnames to IPs and consolidate any duplicate entries
to_add = {}
to_remove = []

for mc_id, log_sources in device_map.items():
    try:
        # Will return IP whether mc_id is IP or hostname
        ip = socket.gethostbyname(mc_id)
    except Exception as host_error:
        logging.error(host_error)
        logging.error("Unable to to resolve hostname {} to IP".format(mc_id))
        continue

    # If mc_id was a hostname that was resolved to an IP
    if ip != mc_id:
        logging.debug("hostname {} resolved to IP {}".format(mc_id, ip))
        if ip in device_map:
            # If this IP is already in the map then consolidate lists
            device_map[ip].extend(log_sources)
            logging.debug("IP {} is in the map, consolidating lists".format(ip))
        else:
            # If this IP is not already in the map then add it
            to_add[ip] = log_sources
            logging.debug("IP {} is not in the map, adding".format(ip))

        # Mark the hostname's entry for deletion
        to_remove.append(mc_id)

        # Need to also update our list of multidomain_ip_list to remove hostnames
        # And add IP to list if it's not already present
        if ip not in multidomain_ip_list:
            multidomain_ip_list.append(ip)
        if mc_id in multidomain_ip_list:
            multidomain_ip_list.remove(mc_id)

# Add entries for IPs that were not already in the map
device_map.update(to_add)

# Remove entries for hostnames that were mapped to IPs
for i in to_remove:
    del device_map[i]
    logging.debug("Removing entry for hostname {}, which has been resolved to an IP".format(i))

# Hostnames resolved, duplicates removed, now output count and list file
with open('mvsCount.csv', 'w') as output:  # pylint: disable=unspecified-encoding
    writer = csv.writer(output)
    writer.writerow(device_map.keys())
    writer.writerows(six.moves.zip_longest(*device_map.values()))

if multidomain:
    mvs_count = multi_domain_count()  # pylint: disable=invalid-name
else:
    mvs_count = len(device_map)  # pylint: disable=invalid-name

print("\nMVS count for the deployment is {}".format(mvs_count))
if multidomain:
    domain_list = list(domain_count_map.keys())
    domain_list.sort()
    for dom in domain_list:
        print("MVS count for domain {} is {}".format(dom, domain_count_map[dom]))

logging.debug("Total log sources considered = {}".format(log_source_count))
