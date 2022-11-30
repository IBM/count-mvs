"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""
# pylint: disable=unused-argument,redefined-outer-name

import pytest
import pexpect
from util.db import Database
from util.log import print_count_mvs_log


def do_setup():
    database = Database()

    # Drop the qradar user
    database.cursor()
    database.drop_qradar_user()
    database.commit()
    database.close()


def do_teardown():
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


def test_fail_to_connect_to_db(setup, pyversion):
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
    assert output[len(output) - 1] == "Unable to connect to database"
