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

domains = [
    {"id": 0, "name": "test1", "deleted": False},
    {"id": 1, "name": "test2", "deleted": False},
    {"id": 2, "name": "test3", "deleted": False},
    {"id": 3, "name": "test4", "deleted": False},
    {"id": 4, "name": "test5", "deleted": False},
]

sensor_devices = [
    {"id": 0, "hostname": "localhost", "devicename": "test1", "devicetypeid": 0, "spconfig": 0},
    {"id": 1, "hostname": "qradar", "devicename": "test2", "devicetypeid": 0, "spconfig": 1},
    {"id": 2, "hostname": "ibm.com", "devicename": "test3", "devicetypeid": 0, "spconfig": 2},
    {"id": 3, "hostname": "example.com", "devicename": "test4", "devicetypeid": 0, "spconfig": 3},
    {"id": 4, "hostname": "test.com", "devicename": "test5", "devicetypeid": 0, "spconfig": 4},
]

sensor_protocol_configs = [
    {"id": 0, "spid": 0},
    {"id": 1, "spid": 1},
    {"id": 2, "spid": 2},
    {"id": 3, "spid": 3},
    {"id": 4, "spid": 4},
]

sensor_protocol_config_parameters = [
    {"id": 0, "sensorprotocolconfigid": 0, "name": "server", "value": "localhost"},
]


def do_setup():
    api = API()

    api.set_search_results_failure(500)

    database = Database()

    # Set up test data
    database.cursor()
    database.create_domains(domains)
    database.create_sensor_devices(sensor_devices)
    database.create_sensor_protocol_configs(sensor_protocol_configs)
    database.create_sensor_protocol_config_parameters(sensor_protocol_config_parameters)
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
    print_count_mvs_log()


@pytest.fixture
def setup():
    do_setup()
    yield
    do_teardown()


def test_fail_http_start_search(setup, pyversion):
    process = pexpect.spawn(f"python{pyversion} python{pyversion}/src/countMVS.py")

    # Give period in days
    process.expect(": ", timeout=7)
    process.sendline("1")

    # Give authentication details
    process.expect(": ", timeout=7)
    process.sendline("1")

    process.expect(": ", timeout=7)
    process.sendline("test_password")

    process.expect(pexpect.EOF, timeout=30)

    output = process.before.decode("utf-8").split("\n")

    process.close()

    # Remove empty strings from output
    output = [x.strip() for x in output if x]

    return_code = process.exitstatus

    # Print stdout/stderr here for debugging in case the test fails
    print(output[len(output) - 6])

    assert return_code == 1
    assert output[len(output) - 1] == "Unable to retrieve domain information. ERROR None"
