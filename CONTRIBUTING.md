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
- Make (installed on most systems by default, for [windows see here](http://gnuwin32.sourceforge.net/packages/make.htm))

### Commands

On your local machine you can format and lint in mostly the same way that the CI pipeline does. There are three
commands you can use:

* `make format`
* `make lint`

These use a local Dockerfile to run these commands, this Dockerfile is set up to be as close to a QRadar environment
as possible (running on Red Hat, using Red Hat Python packages).

### Code style

Pull requests will be accepted only if `make lint` produces no warnings or errors and `make format` results in no
code changes.
