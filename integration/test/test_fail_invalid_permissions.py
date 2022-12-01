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
import json


def do_setup():
    api = API()
    api.set_about_failure(
        401,
        json.dumps({
            "http_response": {"code": 401, "message": "You are unauthorized to access the requested resource."},
            "code": 18, "description": "", "details": {},
            "message": "No SEC header present in request. Please provide it via \"SEC: token\". You may also use BASIC authentication parameters if this host supports it. e.g. \"Authorization: Basic base64Encoding\""
        }))
    database = Database()


def do_teardown():
    api = API()
    api.reset()

    print_count_mvs_log()


@pytest.fixture
def setup():
    do_setup()
    yield
    do_teardown()


def test_user_password(setup, pyversion):
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

    assert return_code == 1
    assert output[len(output) -
                  1] == "You have provided an incorrect password. Please re-run the script and try again."


def test_authorized_service(setup, pyversion):
    process = pexpect.spawn(f"python{pyversion} python{pyversion}/src/countMVS.py")

    # Give period in days
    process.expect(": ", timeout=7)
    process.sendline("1")

    # Give choose authorized service
    process.expect(": ", timeout=7)
    process.sendline("2")

    # Give authorized service
    process.expect(": ", timeout=7)
    process.sendline("test_authorized_service")

    process.expect(pexpect.EOF, timeout=30)

    output = process.before.decode("utf-8").split("\n")

    process.close()

    # Remove empty strings from output
    output = [x.strip() for x in output if x]

    return_code = process.exitstatus

    # Print stdout/stderr here for debugging in case the test fails
    print(output)

    assert return_code == 1
    assert output[len(output) - 1] == "You have provided an incorrect token. Please re-run the script and try again."
