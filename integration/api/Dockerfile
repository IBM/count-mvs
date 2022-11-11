# Copyright 2022 IBM Corporation All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM registry.access.redhat.com/ubi8/ubi-minimal:8.5-218

RUN microdnf install python3 -y
RUN ln -s /usr/bin/python3.6 /usr/local/bin/python

RUN mkdir -p /api

COPY . /api/

RUN python -m pip install -r /api/requirements.txt

WORKDIR /api
