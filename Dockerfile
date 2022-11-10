# Copyright 2022 IBM Corporation All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# This image is used for local development, it is designed to be as close to a QRadar environment as possible.
FROM registry.access.redhat.com/ubi8/ubi-minimal:8.6-994

# Set up Python + RPM dependencies
RUN microdnf install python2 python2-psycopg2 python2-requests python3 python3-devel python3-psycopg2 python3-requests make git gcc -y
RUN ln -s /usr/bin/python3.6 /usr/local/bin/python
RUN ln -s /usr/bin/python3.6 /usr/local/bin/python3
RUN ln -s /usr/bin/python2.7 /usr/local/bin/python2

# Set up dev dependencies
COPY python3/requirements.txt /py3-requirements.txt
COPY python2/requirements.txt /py2-requirements.txt

RUN python3 -m pip install -r /py3-requirements.txt --user
RUN python2 -m pip install -r /py2-requirements.txt --user
