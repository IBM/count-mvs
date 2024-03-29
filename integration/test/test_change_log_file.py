"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""
# pylint: disable=unused-argument,redefined-outer-name

import pytest
import pexpect
from util.db import Database
from util.log import print_count_mvs_log
from os.path import exists
from os import remove

domains = [
    {"id": 0, "name": "test", "deleted": False},
]

sensor_devices = [
    {"id": 0, "hostname": "localhost", "devicename": "test", "devicetypeid": 0, "spconfig": 0},
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


def do_setup():
    database = Database()

    # Set up test data
    database.cursor()
    database.create_domains(domains)
    database.create_sensor_devices(sensor_devices)
    database.create_domain_mappings(domain_mappings)
    database.create_sensor_protocol_configs(sensor_protocol_configs)
    database.create_sensor_protocol_config_parameters(sensor_protocol_config_parameters)
    database.commit()
    database.close()


def do_teardown():
    database = Database()
    database.cursor()
    database.reset()
    database.commit()
    database.close()
    print_count_mvs_log()

    if exists("/var/log/test-log"):
        remove("/var/log/test-log")


@pytest.fixture
def setup():
    do_setup()
    yield
    do_teardown()


def test_change_log_file_output(setup, pyversion):
    process = pexpect.spawn(f"python{pyversion} python{pyversion}/src/countMVS.py -l /var/log/test-log")

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
    assert output[len(output) - 1] == "MVS count for the deployment is 1"
    assert exists("/var/log/test-log")
