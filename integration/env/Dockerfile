# Copyright 2022 IBM Corporation All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM registry.access.redhat.com/ubi8/ubi-minimal:8.5-218

ENV PGHOST='postgres'
ENV PGUSER='qradar'
ENV PGPASSWORD='qradar'

RUN microdnf install python2 python2-psycopg2 python2-requests \
python3 python3-devel python3-psycopg2 python3-requests \
gcc -y
RUN ln -s /usr/bin/python3.6 /usr/local/bin/python3
RUN ln -s /usr/bin/python2.7 /usr/local/bin/python2

# Set up dev dependencies
COPY requirements.txt /
RUN python3 -m pip install -r /requirements.txt --user

# Set up QRadar environment
RUN mkdir -p /var/log/ && mkdir -p /opt/qradar/conf && mkdir -p /opt/qradar/bin
COPY myver /opt/qradar/bin
RUN chmod +x /opt/qradar/bin/myver

# Trust API cert
COPY server.cert /etc/pki/ca-trust/source/anchors/api.cert
RUN update-ca-trust enable

WORKDIR /count-mvs
