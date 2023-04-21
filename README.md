[![Build Status](https://github.com/ibm/count-mvs/workflows/build/badge.svg)](https://github.com/ibm/count-mvs/actions)
[![Python 3 Security Rating](https://sonarcloud.io/api/project_badges/measure?project=count-mvs-py3&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=count-mvs-py3)
[![Python 2 Security Rating](https://sonarcloud.io/api/project_badges/measure?project=count-mvs-py2&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=count-mvs-py2)

# Count MVS

## What is the purpose of this script?

This script is designed to give an MVS count for your QRadar deployment when run on your QRadar console.

## What does MVS stand for?

MVS stands for Managed Virtual Server

## What counts as an MVS?

MVS can be:

*  A physical or virtual server that can be seen by the environment e.g. Actual servers(Windows, Linux), VMs, EC2s

MVS can not be:

* An endpoint (laptop)
* A SaaS service

## How do I run the script?

The script is available in both Python 2 and Python 3, if you are on QRadar 7.5.0+/7.4.3 FP6+ you can use the Python 3
script.

### Python 2

1. Copy the [Python 2 countMVS.py](python2/src/countMVS.py) script to your QRadar console.
2. Make sure it has the correct permissions to execute by running this `chmod` command:

```bash
chmod +x countMVS.py
```

3. Execute the script:

```
./countMVS.py
```

### Python 3

1. Copy the [Python 3 countMVS.py](python3/src/countMVS.py) script to your QRadar console.
2. Make sure it has the correct permissions to execute by running this `chmod` command:

```bash
chmod +x countMVS.py
```

3. Execute the script:

```
./countMVS.py
```

<a name="commandlineswitches"></a>
### Command line Switches

There are a number of command line switches that can be used with the script. To see a listing of the available command
line switches simply add `--help` or `-h`.

```bash
python ./countMVS.py --help
usage: countMVS.py [-h] [-d] [-i] [-w] [-o <filename>] [-l <filename>]

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           sets the log level to debug
  -i, --insecure        skips certificate verification for HTTP requests
  -w, --skip-workstation-check
                        skip windows workstation check
  -o <filename>         overrides the default output csv file
  -l <filename>         overrides the default file to log to
```

Let's look at each switch in turn.

* `-h` or `--help` - Displays the usage message displayed above with all of the command line switches that can be used with the script
* `-d` or `--debug` - This command line switch is used to toggle the logging level for the script. As stated in
the [Output from the script](#outputfromscript) section the script outputs to a log file under `/var/log` called
`countMVS.log` by default. When you execute the script it will log at **INFO** level however if you wish to add extra
logging at **DEBUG** level you can do so by adding this switch
* `-i` or `--insecure` - This command line switch is used to skip certificate verification for API calls made to the
QRadar API by the script. By default all API calls use certificate verification, but this can be skipped by providing
this flag if the certificates on your QRadar system have expired or are broken.
* `-w` or `--skip-workstation-check` - This can be used to skip the check for Windows workstations. Windows workstations do not count as MVS and by default will be removed from the MVS count however the process for determining this is time consuming. If you wish to skip this check use this command line switch. **Note**: You will have to remove any Windows workstations manually from the MVS count result
* `-o <filename>` - This command line switch is used to override the default csv file name used to output the results
from the script. By default this is mvsCount.csv however this can be overridden with this switch to a filename of the
user's choice
* `-l <filename>` - This command line switch is used to override the default file the script logs to. By default this
is `/var/log/countMVS.log` however this can be overridden with this switch to a filename of the user's choice

## High level description of how the script works

In order to calculate an MVS count from a QRadar deployment the script must perform the following high level actions:

* Search the Postgres database for any log sources that have processed events within a set time period (1 day by
default with a max time period of 10 days for performance reasons)
* Determine whether the QRadar deployment has a single domain or multiple domain set up. If there are multiple domains
as some log sources do not directly map via the database to individual domains an AQL search will need to be performed
via the REST API to determine which domain(s) a log source is associated with
* The script should only be runnable on the console
* The script should prompt for either the admin user password or an authorized service token with admin capabilities
which the user must paste in
* A check must be made on the authorized service token that it has ADMIN capabilities which are required to make the
REST API call to execute an AQL query on QRadar
* Appropriate error messages should be displayed to the user if passwords or tokens are incorrect or do not have the
required capabilities to proceed
* Perform the AQL query via the REST API to calculate the log source to domain mapping if the deployment is set up for
multiple domains. The AQL query is not required if we only have the Default domain and all log sources can assume that
domain rather than performing the search
* Loop through each of the log sources and check if they log sources match a list of excluded log source types which do
not count as MVS
* Build a map of hostnames/IP's to log sources using either the hostname field in the database for the log source or
use the associated sensor protocol parameters to calculate the hostname/IP
* If the skip workstation check switch has not been passed to the script it removes any Windows workstations from the map. This is to be calculated using the REST API again using Windows Event
IDs to calculate the associated QIDs and then search using ariel for matches to determine if the machines are Windows
workstations or servers
* Resolve any hostnames in the map to IP addresses so that we can compare log sources correctly as some may have
hostnames and some may have IP addresses
* If the setup has multiple domains a given IP could refer to multiple servers/machines. In this case if the same
IP/hostname appears in multiple domains we count each occurance as a separate MVS i.e. if the same IP appeared in
domain one and domain two that then counts as two MVS
* Produce a report with the MVS count showing a list of log sources to IP/Hostnames
* Output a listing of domains to MVS count

<a name="outputfromscript"></a>
## Output from the script

The countMVS.py script produces the following as output:

* A csv file (mvsCount.csv by default, this filename can be overriden by a command line switch) which contains a
listing of:
   * The MVS count for the deployment
	* The Time period selected by the user for the last time seen for events from log sources to be considered in the count
	* If the Windows workstation check was skipped or not. If it has been skipped Windows workstations will need to be manually removed from the results to calculate the MVS count
	* A summary of how many log sources were processed, skipped and excluded in the count results
	* If there are multiple domains in the deployment a summary of the counts per domain
	* A listing of each of the MVS in the deployment
	* A listing of log source to MVS IP/Hostname (with log source data horizontally for easier viewing by the user)
	* A listing of any excluded log sources e.g. Windows workstation log sources or excluded log sources by type, any
    skipped log sources (this may be log sources that we failed to parse the domain for)
* Output to the screen at the end of the execution of the script with the MVS count for the deployment along with a
summary breakdown by domain name if the system has multiple domains
* A log file containing information about the execution of the script (/var/log/countMVS.log by default, this filename
can also be overriden by a command line switch). The logging to this file is set at INFO level by default but can be
changed by adding a command line switch to DEBUG level if required

Example output:

```csv
Results Summary:
MVS Count = 2
Data Period In Days = 5
Windows Workstation Check Skipped = False
Log Sources Processed = 8
Log Sources Skipped = 0
Log Sources Excluded = 1

MVS Count By Domain:
Domain Name, MVS Count
Default Domain,2

MVS List:
127.0.0.1
127.0.0.2

Log Source Details:
MVS Device Id = 127.0.0.1
ID,Name,Log Source Identifier,Type ID,Last Seen,SP Config,Domains
72,ISA @ 127.0.0.1,127.0.0.1,191,1653311211964,0,['Default Domain']

MVS Device Id = 127.0.0.2
ID,Name,Log Source Identifier,Type ID,Last Seen,SP Config,Domains
74,MicrosoftDHCP @ microsoft.dhcp.test.com,microsoft.dhcp.test.com,97,1653311397947,0,['Default Domain']
73,ISA @ microsoft.isa.test.com,microsoft.isa.test.com,191,1653311243354,0,['Default Domain']
71,MicrosoftExchange @ microsoft.exchange.test.com,microsoft.exchange.test.com,99,1653310035730,0,['Default Domain']
70,MicrosoftIAS @ microsoft.ias.test.com,microsoft.ias.test.com,98,1653310030759,0,['Default Domain']
75,WindowsAuthServer @ microsoft.windows.test.com,microsoft.windows.test.com,12,1653313524268,0,['Default Domain']
77,MicrosoftSQL @ microsoft.sql.test.com,microsoft.sql.test.com,101,1653313531070,0,['Default Domain']

Excluded Log Source Details:
Windows Workstations:
MVS Device Id = 127.0.0.1
ID,Name,Log Source Identifier,Type ID,Last Seen,SP Config,Domains
76,WindowsAuthServer @ 127.0.0.1,127.0.0.1,12,1653313441854,0,['Default Domain']
```

## Contributing

See the [contributing document](./CONTRIBUTING.md) for information about contributing to this project and developing it.
