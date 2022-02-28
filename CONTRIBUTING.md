# Contributing

To contribute code or documentation, please submit a [pull request](https://github.com/ibm/count-mvs/pulls).

## Proposing new features

If you would like to implement a new feature, please [raise an issue](https://github.com/ibm/count-mvs/issues) before
sending a pull request so that the feature can be discussed.

## Fixing bugs

To fix a bug, please [raise an issue](https://github.ibm.com/ibm/count-mvs/issues) before sending a pull request so
that the bug can be tracked.

## Merge approval

Any change requires approval before it can be merged.
A list of maintainers can be found on the [maintainers page](MAINTAINERS.md).

## Legal

Each source file must include a license header for the Apache Software License 2.0.
Using the SPDX format is the simplest approach. See existing source files for an example.

## Development

To make code changes follow the steps outlined here.

### Dependencies

Developing this project requires some dependencies:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Make (installed on most systems by default, for [windows see here](http://gnuwin32.sourceforge.net/packages/make.htm))

### Commands

On your local machine you can format, lint, and test in mostly the same way that the CI pipeline does. These are the
commands you can use:

* `make format` - format the code
* `make lint` - run a linter against the code
* `make test` - run all of the tests against the code
* `make integration_tests` - run all of the integration tests
* `make py3_integration_tests` - runs the integration tests in Python 3 mode
* `make py2_integration_tests` - runs the integration tests in Python 3 mode
* `make unit_tests` - run all of the unit tests
* `make integration_tests INTEGRATION_TESTS=integration/test/test_single_domain.py` - run a single integration test
(`integration/test/test_single_domain.py`), this also works for the `py3_integration_tests` and `py2_integration_tests`
targets
* `make unit_tests UNIT_TESTS=test/test_example.py` - run a single unit test (`test/test_example.py`)

These use a local Dockerfile to run these commands, this Dockerfile is set up to be as close to a QRadar environment
as possible (running on Red Hat, using Red Hat Python packages).

### Code style

Pull requests will be accepted only if `make lint` produces no warnings or errors, `make format` results in no code
changes, and `make test` passes without failure.

### How does the build pipeline work?

You don't need to read this section to develop, this documentation is just here in case a change needs to be made to
the build pipeline.

#### Linting and formatting

Linting and formatting run inside a Docker container defined by [the Dockerfile in the root of this
project](./Dockerfile). This Dockerfile is set up to be a minimal Red Hat environment using the UBI8 Docker image, this
is to be as similar to QRadar as possible, so Python dependencies are installed from Red Hat packages (apart from the
dev tools which aren't on QRadar).

For example when `make format` is run it will build the Docker image if it is not already built, then it will
load the project in as a volume, before running `make format_local` in the Docker container, which will actually
run the Python formatter.

### Testing

See the [testing document](./TESTING.md).
