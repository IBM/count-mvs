# Copyright 2022 IBM Corporation All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM postgres:11.14

ENV POSTGRES_USER=qradar
ENV POSTGRES_DB=qradar
ENV POSTGRES_PASSWORD=qradar

ADD ./integration/db/schema.sql /docker-entrypoint-initdb.d/
