# Copyright 2022 IBM Corporation All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# This image is used for local development, it is designed to be as close to a QRadar environment as possible.
FROM registry.access.redhat.com/ubi8/ubi-minimal:8.5-218

# Set up Python + RPM dependencies
RUN microdnf install python3 python3-devel python3-psycopg2 python3-requests make git gcc -y
RUN ln -s /usr/bin/python3.6 /usr/local/bin/python

# Set up dev dependencies
COPY requirements.txt /
RUN python -m pip install -r /requirements.txt --user
