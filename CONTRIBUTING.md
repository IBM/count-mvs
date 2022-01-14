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
A list of maintainers can be found on the [MAINTAINERS](MAINTAINERS.md) page.

## Legal

Each source file must include a license header for the Apache Software License 2.0.
Using the SPDX format is the simplest approach. See existing source files for an example.

## Development

To make code changes follow the steps outlined here.

### Dependencies

Developing this project requires some dependencies:

- [Python 3.6.x](https://www.python.org/downloads/release/python-360/) and pip (Consider using
[pyenv](https://github.com/pyenv/pyenv) to manage Python versions)
- Make (installed on most systems by default, for [windows see here](http://gnuwin32.sourceforge.net/packages/make.htm))

Once you have installed the above dependencies, project dependencies can be installed by using pip:

```bash
pip install -r requirements-dev.txt
```

The `requirements-dev.txt` file contains the Python packages needed to run this tool.

### Commands

On your local machine you can format and lint in mostly the same way that the CI pipeline does. There are three
commands you can use:

* `make format`
* `make lint`

### Code style

Pull requests will be accepted only if `make lint` produces no warnings or errors and `make format` results in no
code changes.
