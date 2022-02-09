import pytest
import pexpect
from util.db import Database
from util.api import API

domains = [{
    "id": 0,
    "name": "test1",
}, {
    "id": 1,
    "name": "test2",
}, {
    "id": 2,
    "name": "test3",
}, {
    "id": 3,
    "name": "test4",
}, {
    "id": 4,
    "name": "test5",
}]

sensor_devices = [{
    "id": 0,
    "hostname": "localhost",
    "devicename": "test1",
    "devicetypeid": 0,
    "spconfig": 0
}, {
    "id": 1,
    "hostname": "qradar",
    "devicename": "test2",
    "devicetypeid": 0,
    "spconfig": 1
}, {
    "id": 2,
    "hostname": "ibm.com",
    "devicename": "test3",
    "devicetypeid": 0,
    "spconfig": 2
}, {
    "id": 3,
    "hostname": "example.com",
    "devicename": "test4",
    "devicetypeid": 0,
    "spconfig": 3
}, {
    "id": 4,
    "hostname": "test.com",
    "devicename": "test5",
    "devicetypeid": 0,
    "spconfig": 4
}]

sensor_protocol_configs = [{
    "id": 0,
    "spid": 0
}, {
    "id": 1,
    "spid": 1
}, {
    "id": 2,
    "spid": 2
}, {
    "id": 3,
    "spid": 3
}, {
    "id": 4,
    "spid": 4
}]

sensor_protocol_config_parameters = [{
    "id": 0,
    "sensorprotocolconfigid": 0,
    "name": "server",
    "value": "localhost"
}]

search_data = {
    "events": [{
        "domain_id": 0,
    }]
}


def test_single_domain():
    api = API()

    api.set_search_data(search_data)

    db = Database()

    # Clear any leftover artifacts
    db.cursor()
    db.reset()
    db.commit()

    # Set up test data
    db.cursor()
    db.create_domains(domains)
    db.create_sensor_devices(sensor_devices)
    db.create_sensor_protocol_configs(sensor_protocol_configs)
    db.create_sensor_protocol_config_parameters(
        sensor_protocol_config_parameters)
    db.commit()

    process = pexpect.spawn("python countMVS.py")

    # Give authentication details
    process.expect("(q to quit)*", timeout=5)
    process.sendline("1")

    process.expect("Please input the Admin user password:*", timeout=5)
    process.sendline("qradar.1")

    process.expect(pexpect.EOF, timeout=5)

    output = process.before.decode("utf-8").split("\n")

    process.close()

    # Remove empty strings from output
    output = [x.strip() for x in output if x]

    return_code = process.exitstatus

    # Print stdout/stderr here for debugging in case the test fails
    print(output)

    assert (return_code == 0)
    assert (output[len(output) - 1] == "MVS count for domain Default is 5")

    # Cleanup
    db.cursor()
    db.reset()
    db.commit()
    db.close()
