-- Copyright 2022 IBM Corporation All Rights Reserved.
-- SPDX-License-Identifier: Apache-2.0

CREATE ROLE qradar WITH LOGIN SUPERUSER PASSWORD 'qradar';

CREATE TABLE public.domains (
    id integer NOT NULL,
    name character varying(1024),
    deleted boolean NOT NULL default false,
    PRIMARY KEY (id)
);

ALTER TABLE public.domains OWNER TO integration;

CREATE TABLE public.sensordevice (
    id integer NOT NULL,
    hostname character varying(1275) NOT NULL,
    devicename character varying(1275) NOT NULL,
    devicetypeid integer,
    spconfig bigint,
    timestamp_last_seen bigint DEFAULT 0 NOT NULL,
    PRIMARY KEY (id)
);

ALTER TABLE public.sensordevice OWNER TO integration;

CREATE TABLE public.domain_mapping (
    id integer NOT NULL,
    domain_id integer,
    source_type integer,
    source_id bigint,
    PRIMARY KEY (id),
    FOREIGN KEY (domain_id) REFERENCES public.domains(id)
);

ALTER TABLE public.domain_mapping OWNER TO integration;

CREATE TABLE public.sensorprotocolconfig (
    id bigint NOT NULL,
    spid bigint,
    PRIMARY KEY (id)
);

ALTER TABLE public.sensorprotocolconfig OWNER TO integration;

CREATE TABLE public.sensorprotocolconfigparameters (
    id bigint NOT NULL,
    sensorprotocolconfigid bigint,
    name character varying(255) NOT NULL,
    value character varying(1275) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (sensorprotocolconfigid) REFERENCES sensorprotocolconfig(id)
);

ALTER TABLE public.sensorprotocolconfigparameters OWNER TO integration;

CREATE TABLE public.qidmap (
    id bigint NOT NULL,
    qid integer,
    PRIMARY KEY (id)
);

ALTER TABLE public.qidmap OWNER TO integration;

CREATE TABLE public.dsmevent (
    id bigint NOT NULL,
    qidmapid bigint,
    devicetypeid integer,
    deviceeventid integer,
    PRIMARY KEY (id),
    FOREIGN KEY (qidmapid) REFERENCES qidmap(id)
);

ALTER TABLE public.dsmevent OWNER TO integration;

-- This must be the last thing inserted, this allows the integration script to know when it's safe to run
CREATE TABLE ready_for_testing (
    id integer NOT NULL
);

INSERT INTO ready_for_testing(id) VALUES(0);
