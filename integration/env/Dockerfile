# Copyright 2022 IBM Corporation All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM registry.access.redhat.com/ubi8/ubi-minimal:8.5-218

ENV PGHOST='postgres'
ENV PGUSER='qradar'
ENV PGPASSWORD='qradar'

RUN microdnf install python3 python3-psycopg2 python3-requests -y
RUN ln -s /usr/bin/python3.6 /usr/local/bin/python

# Set up dev dependencies
COPY requirements.txt /
RUN python -m pip install -r /requirements.txt --user

# Set up QRadar environment
RUN mkdir -p /var/log/ && mkdir -p /opt/qradar/conf
COPY integration/env/nva.hostcontext.conf /opt/qradar/conf/nva.hostcontext.conf

# Trust API cert
COPY integration/api/server.cert /etc/pki/ca-trust/source/anchors/api.cert
RUN update-ca-trust enable

WORKDIR /count-mvs