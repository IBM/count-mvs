# Testing

This document explains how the tests are set up for this project.

# Unit tests

Unit tests run inside a Docker container defined by [the Dockerfile in the root of this project](./Dockerfile). This
Dockerfile is set up to be a minimal Red Hat environment using the UBI8 Docker image, this is to be as similar to
QRadar as possible, so Python dependencies are installed from Red Hat packages (apart from the dev tools which
aren't on QRadar).

The unit tests are run using PyTest.

The unit tests for this project are stored in the `/test` directory.

# Integration tests

Integration tests are run using Docker Compose, this allows for multiple Docker containers to be orchestrated to run
together. This allows for the integration tests to set up a test PostgreSQL database in a Docker container, a
mock QRadar API in another container, and a QRadar test environment in another container. This allows the script to
be run in a simulated QRadar environment, allowing testing without requiring a QRadar system.

When running the integration tests, they are run using PyTest, with this project mounted into the QRadar test
environment container, with any logs generated mounted from `/log` in the project's root directory.

The integration tests for this project (and any integration dependencies such as Dockerfiles and SQL files) are stored
in the `/integration` directory.

## Mock DB

The mock database is set up using a PostgreSQL Docker image, when the container starts a schema is loaded into the
database which is a stripped back version of the tables that would be found on the QRadar database.

## Mock API

The mock API provides a simplified interface for the QRadar Ariel searches endpoints. This is set up by a simple
Flask web server which runs in a Docker container. This flask endpoint exposes a couple of endpoints for mocking the
Ariel searches endpoints, and it also exposes some configuration endpoints to help with testing.

The mock API just stores test data in memory.

You can make each endpoint return a different status code to simulate failures.

You can add a list of search data for the results endpoint to return, when a search is created the search results
will be assigned to each created search and then the results can be queried. This happens in a queue approach, so
if you add in 4 search results, the next 4 searches created will be assigned this search data.

## Mock QRadar environment

The QRadar environment is mocked using the Red Hat Universal Base Image, this is set up to have the required
Python dependencies installed through Red Hat packages, and it has a couple of files added that the script expects
on QRadar (e.g. `nva.hostcontext.conf`).

## Test utilities

The integration tests are set up with some utility functions for setting up mock database and API values. For example:

```python
db = Database()

# Set up test data
db.cursor()
db.create_domains(domains)
db.create_sensor_devices(sensor_devices)
db.create_sensor_protocol_configs(sensor_protocol_configs)
db.create_sensor_protocol_config_parameters(
    sensor_protocol_config_parameters)
db.commit()
db.close()
```

This sets up some test data for an integration test, creating domains, sensor devices, etc.

Each test should be self contained, so make sure in each tests teardown all test data is cleaned up:

```python
import pytest
from util.db import Database
from util.api import API
from util.log import print_count_mvs_log

def do_setup():
    # Do setup here
    pass

def do_teardown():
    api = API()
    api.reset()
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
```
