"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import pytest
import psycopg2
import time

POSTGRES_RETRIES = 10
POSTGRES_WAIT_INTERVAL = 3


def wait_until_db_ready():
    retries = 0
    db_ready = False
    while not db_ready and retries < POSTGRES_RETRIES:
        retries += 1
        try:
            conn = psycopg2.connect("dbname='qradar' user='qradar'")
            cur = conn.cursor()

            cur.execute("select count(id) from ready_for_testing;")
            ready_for_testing = int(cur.fetchone()[0])
            if ready_for_testing > 0:
                db_ready = True
            conn.close()
        except Exception as e:
            time.sleep(POSTGRES_WAIT_INTERVAL)
    if not db_ready:
        raise Exception(
            f"PostgreSQL DB not ready after waiting for {POSTGRES_RETRIES * POSTGRES_WAIT_INTERVAL} seconds")


def pytest_addoption(parser):
    parser.addoption("--pyversion", action="store", default="3", help="python version: 2 or 3")


@pytest.fixture
def pyversion(request):
    return request.config.getoption("--pyversion")


def pytest_sessionstart(session):
    wait_until_db_ready()
