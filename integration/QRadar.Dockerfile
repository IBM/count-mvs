# Copyright 2022 IBM Corporation All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM registry.access.redhat.com/ubi8/ubi-minimal:8.5-218

ENV PGHOST='postgres'
ENV PGUSER='qradar'
ENV PGPASSWORD='qradar'

RUN microdnf install python3 python3-psycopg2 python3-requests -y
RUN ln -s /usr/bin/python3.6 /usr/local/bin/python

RUN mkdir -p /var/log/
