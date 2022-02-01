-- Copyright 2022 IBM Corporation All Rights Reserved.
-- SPDX-License-Identifier: Apache-2.0

CREATE TABLE public.domains (
    id integer NOT NULL,
    name character varying(1024)
);

ALTER TABLE public.domains OWNER TO qradar;

CREATE TABLE public.sensordevice (
    id integer NOT NULL,
    hostname character varying(1275) NOT NULL,
    devicename character varying(1275) NOT NULL,
    devicetypeid integer,
    spconfig bigint,
    timestamp_last_seen bigint DEFAULT 0 NOT NULL
);

ALTER TABLE public.sensordevice OWNER TO qradar;

INSERT INTO public.domains(id, name)
    VALUES(0, 'test');

INSERT INTO public.sensordevice(id, hostname, devicename, devicetypeid, spconfig, timestamp_last_seen)
    VALUES(0, 'test', 'test', 0, 0, 0);
