import pytest
import pexpect
from util.db import Database
from util.log import print_count_mvs_log

domains = [{
    "id": 0,
    "name": "test",
}]

sensor_devices = [{
    "id": 0,
    "hostname": "localhost",
    "devicename": "test",
    "devicetypeid": 0,
    "spconfig": 0
}]

domain_mappings = [{"id": 0, "domain_id": 0, "source_type": 2, "source_id": 0}]

sensor_protocol_configs = [{"id": 0, "spid": 0}]

sensor_protocol_config_parameters = [{
    "id": 0,
    "sensorprotocolconfigid": 0,
    "name": "server",
    "value": "localhost"
}]


def do_setup():
    db = Database()

    # Set up test data
    db.cursor()
    db.create_domains(domains)
    db.create_sensor_devices(sensor_devices)
    db.create_domain_mappings(domain_mappings)
    db.create_sensor_protocol_configs(sensor_protocol_configs)
    db.create_sensor_protocol_config_parameters(
        sensor_protocol_config_parameters)
    db.commit()
    db.close()


def do_teardown():
    db = Database()
    db.cursor()
    db.reset()
    db.commit()
    db.close()
    print_count_mvs_log()


@pytest.fixture
def setup():
    do_setup()
    yield
    do_teardown()


def test_single_domain(setup):
    process = pexpect.spawn("python countMVS.py")
    process.expect(pexpect.EOF, timeout=5)

    output = process.before.decode("utf-8").split("\n")

    process.close()

    # Remove empty strings from output
    output = [x.strip() for x in output if x]

    return_code = process.exitstatus

    # Print stdout/stderr here for debugging in case the test fails
    print(output)

    assert (return_code == 0)
    assert (output[len(output) - 1] == "MVS count for the deployment is 1")
