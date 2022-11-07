# Testing

This document explains how the tests are set up for this project.

# Unit tests

Unit tests run inside a Docker container defined by [the Dockerfile in the root of this project](./Dockerfile). This
Dockerfile is set up to be a minimal Red Hat environment using the UBI8 Docker image, this is to be as similar to
QRadar as possible, so Python dependencies are installed from Red Hat packages (apart from the dev tools which
aren't on QRadar).

The unit tests are run using PyTest.

The unit tests for this project are stored in the `/test` directory.
