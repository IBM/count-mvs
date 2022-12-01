"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""
# pylint: disable=unused-argument,redefined-outer-name

import pytest
import pexpect
from util.log import print_count_mvs_log


def do_teardown():
    print_count_mvs_log()


@pytest.fixture
def setup():
    yield
    do_teardown()


def test_fail_is_console(setup, pyversion):
    process = pexpect.spawn(
        f'/bin/bash -c "MYVER_FAIL_IS_CONSOLE=true python{pyversion} python{pyversion}/src/countMVS.py"')

    process.expect(pexpect.EOF, timeout=5)

    output_lines = process.before.decode("utf-8").split("\n")
    process.close()
    output_lines = [x.strip() for x in output_lines if x]

    assert process.exitstatus == 1
    assert output_lines[0] == "This script can only be ran on the console. Exiting..."


def test_fail_hostname(setup, pyversion):
    process = pexpect.spawn(
        f'/bin/bash -c "MYVER_FAIL_HOSTNAME=true python{pyversion} python{pyversion}/src/countMVS.py"')

    # Give period in days
    process.expect(": ", timeout=7)
    process.sendline("1")

    # Give choose admin user
    process.expect(": ", timeout=7)
    process.sendline("1")

    # Give password
    process.expect(": ", timeout=7)
    process.sendline("test_password")

    process.expect(pexpect.EOF, timeout=5)

    output = process.before.decode("utf-8").split("\n")
    process.close()
    output = [x.strip() for x in output if x]

    expected_message = "Command '['/opt/qradar/bin/myver', '-vh']' returned non-zero exit status 1."
    if pyversion == "2":
        # In Python 2 this error is returned without a '.'
        expected_message = "Command '['/opt/qradar/bin/myver', '-vh']' returned non-zero exit status 1"

    assert process.exitstatus == 1
    assert output[len(output) - 1] == expected_message
