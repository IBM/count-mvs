# Count MVS

This is a script that is meant to be ran on a Qradar Console and give a count of the MVS (Managed Virtual Servers) for
the deployment.

To run the script you need to copy it to the Console, make it executable `chmod +x countMVS.py`, and then run the
script with `./countMVS.py`. If your deployment is a multi-tenant environment (i.e. it receives events from multiple
domains) then you will be prompted for authentication. You can choose between running the script as the Admin user, or
using an Authorized Service with the Admin Security Profile. After you choose the script will prompt you for either the
Admin user's password or the Authorized Service's security token before executing.

The script works by querying the database to compile a list of log sources that have sent events to Qradar within the
last 24 hours. From that list of log sources we build a list of the machines those sources are running on. If there are
any log sources that are not explicitly running on a machine we consider an MVS, for example a SaaS service, then we
remove those log sources from the list. In this version of the script we have a list of log sources we consider as not
running on an MVS, we plan on improving our algorithm for determining log sources are/are not running on an MVS. After
we filter out those log sources we ensure that no machine in the list  is referenced more than once. Finally we output
the list, a map of MVS IPs to a list of each of their log sources, to a file and return the final count of MVS the
deployment has received events from in the last 24 hours

There are additional considerations for multi-tenant environments, as the script needs to consider the case where a
given IP could refer to multiple different machines across multiple domains, which would affect our MVS count. If the
script detects that a log source has received events from multiple domains then it will try to compile a list of those
domains by issuing calls to the Ariel API in order to inspect the events that were sent to that log source in the last
24 hours. These API calls are why the script requires authentication in this case. If we find a log source has been
receiving events from the same IP from different domains then that means the IP represents multiple machines, and this
will be reflected in the MVS count. We include the list of domains for each log source in the csv output file. In
addition to the MVS count for the entire deployment, in this case we will also provide a separate MVS count for each
domain.

The script generates the `MVScount.csv` file. The header of the file is a list of the IP of each MVS, and the columns
are the list of log sources for each MVS.

## Contributing

See the [contributing document](./CONTRIBUTING.md) for information about contributing to this project and developing it.
