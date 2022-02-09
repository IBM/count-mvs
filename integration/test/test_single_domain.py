import pytest
import pexpect
from util.db import Database

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


def test_single_domain():
    db = Database()

    # Clear any leftover artifacts
    db.cursor()
    db.reset()
    db.commit()

    # Set up test data
    db.cursor()
    db.create_domains(domains)
    db.create_sensor_devices(sensor_devices)
    db.create_domain_mappings(domain_mappings)
    db.create_sensor_protocol_configs(sensor_protocol_configs)
    db.create_sensor_protocol_config_parameters(
        sensor_protocol_config_parameters)
    db.commit()

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

    # Cleanup
    db.cursor()
    db.reset()
    db.commit()
    db.close()
