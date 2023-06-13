"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""
# pylint: disable=unused-argument,redefined-outer-name

import pytest
import pexpect
from util.db import Database
from util.api import API
from util.log import print_count_mvs_log
from os.path import exists
from os import remove

domains = [
    {"id": 0, "name": "test", "deleted": False},
]

sensor_devices = [
    {
        "id": 0, "hostname": "windows-workstation-1", "devicename": "windows-workstation-1", "devicetypeid": 12,
        "spconfig": 0
    },
    {
        "id": 1, "hostname": "windows-workstation-2", "devicename": "windows-workstation-2", "devicetypeid": 12,
        "spconfig": 0
    },
    {"id": 2, "hostname": "windows-server", "devicename": "windows-server", "devicetypeid": 12, "spconfig": 0},
    {
        "id": 3, "hostname": "windows-sql-server", "devicename": "windows-sql-server", "devicetypeid": 101,
        "spconfig": 0
    },
    {"id": 4, "hostname": "windows-iis", "devicename": "windows-iis", "devicetypeid": 13, "spconfig": 0},
    {"id": 5, "hostname": "windows-exchange", "devicename": "windows-exchange", "devicetypeid": 99, "spconfig": 0},
]

domain_mappings = [
    {"id": 0, "domain_id": 0, "source_type": 2, "source_id": 0},
]

sensor_protocol_configs = [
    {"id": 0, "spid": 0},
]

sensor_protocol_config_parameters = [
    {"id": 0, "sensorprotocolconfigid": 0, "name": "server", "value": "localhost"},
]

qidmap_configs = [{"id": 0, "qid": 0}, {"id": 1, "qid": 1}, {"id": 2, "qid": 2}, {"id": 3, "qid": 3},
                  {"id": 4, "qid": 4}]

dsm_event_configs = [
    {"id": 0, "qidmapid": 0, "devicetypeid": 12, "deviceeventid": 4768},
    {"id": 1, "qidmapid": 1, "devicetypeid": 12, "deviceeventid": 4727},
    {"id": 2, "qidmapid": 2, "devicetypeid": 12, "deviceeventid": 4728},
    {"id": 3, "qidmapid": 3, "devicetypeid": 12, "deviceeventid": 4729},
]

search_data = [{"events": []}, {"events": []}, {"events": [{"logsourceid": 0, "domainname_domainid": "test1"}]},
               {"events": [{"logsourceid": 0, "domainname_domainid": "test1"}]},
               {"events": [{"logsourceid": 0, "domainname_domainid": "test1"}]},
               {"events": [{"logsourceid": 0, "domainname_domainid": "test1"}]}]


def do_setup():
    api = API()
    api.add_search_data(search_data)

    database = Database()
    # Set up test data
    database.cursor()
    database.create_domains(domains)
    database.create_sensor_devices(sensor_devices)
    database.create_domain_mappings(domain_mappings)
    database.create_sensor_protocol_configs(sensor_protocol_configs)
    database.create_sensor_protocol_config_parameters(sensor_protocol_config_parameters)
    database.create_qidmaps(qidmap_configs)
    database.create_dsm_events(dsm_event_configs)
    database.commit()
    database.close()


def do_teardown():
    api = API()
    api.reset()

    database = Database()
    database.cursor()
    database.reset()
    database.commit()
    database.close()

    # Remove windows workstation lookup caching
    if exists(".windows_workstations"):
        remove(".windows_workstations")

    print_count_mvs_log()


@pytest.fixture
def setup():
    do_setup()
    yield
    do_teardown()


def test_mixed_windows_servers_workstations(setup, pyversion):
    process = pexpect.spawn(f"python{pyversion} python{pyversion}/src/countMVS.py")

    # Give period in days
    process.expect(": ", timeout=7)
    process.sendline("1")

    # Give choose admin user
    process.expect(": ", timeout=7)
    process.sendline("1")

    # Give password
    process.expect(": ", timeout=7)
    process.sendline("test_password")

    process.expect(pexpect.EOF, timeout=30)

    output = process.before.decode("utf-8").split("\n")

    process.close()

    # Remove empty strings from output
    output = [x.strip() for x in output if x]

    return_code = process.exitstatus

    # Print stdout/stderr here for debugging in case the test fails
    print(output)

    assert return_code == 0
    assert output[len(output) - 1] == "MVS count for the deployment is 4"


def test_skipping_windows_workstation_check(setup, pyversion):
    process = pexpect.spawn(f"python{pyversion} python{pyversion}/src/countMVS.py -w")

    # Give period in days
    process.expect(": ", timeout=7)
    process.sendline("1")

    # Give choose admin user
    process.expect(": ", timeout=7)
    process.sendline("1")

    # Give password
    process.expect(": ", timeout=7)
    process.sendline("test_password")

    process.expect(pexpect.EOF, timeout=30)

    output = process.before.decode("utf-8").split("\n")

    process.close()

    # Remove empty strings from output
    output = [x.strip() for x in output if x]

    return_code = process.exitstatus

    # Print stdout/stderr here for debugging in case the test fails
    print(output)

    assert return_code == 0
    assert output[len(output) - 1] == "MVS count for the deployment is 6"
