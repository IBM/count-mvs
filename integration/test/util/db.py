"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import psycopg2


class Database:
    def __init__(self) -> None:
        self.conn = psycopg2.connect("dbname='qradar' user='integration'")
        self.cur = None

    def cursor(self) -> None:
        self.cur = self.conn.cursor()

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        if self.cur:
            self.cur.close()
        self.conn.close()

    def create_domains(self, domains) -> None:
        for domain in domains:
            self.cur.execute("INSERT INTO public.domains(id, name) VALUES(%s, %s);", (domain["id"], domain["name"]))

    def create_sensor_devices(self, sensor_devices) -> None:
        for sensor_device in sensor_devices:
            self.cur.execute(
                """
            INSERT INTO
            public.sensordevice(id, hostname, devicename, devicetypeid, spconfig, timestamp_last_seen)
            VALUES(%s, %s, %s, %s, %s, extract(epoch from now())  * 1000);
            """, (sensor_device["id"], sensor_device["hostname"], sensor_device["devicename"],
                  sensor_device["devicetypeid"], sensor_device["spconfig"]))

    def create_domain_mappings(self, domain_mappings) -> None:
        for domain_mapping in domain_mappings:
            self.cur.execute(
                "INSERT INTO public.domain_mapping(id, domain_id, source_type, source_id) VALUES(%s, %s, %s, %s);",
                (domain_mapping["id"], domain_mapping["domain_id"], domain_mapping["source_type"],
                 domain_mapping["source_id"]))

    def create_sensor_protocol_configs(self, sensor_protocol_configs) -> None:
        for sensor_protocol_config in sensor_protocol_configs:
            self.cur.execute("INSERT INTO public.sensorprotocolconfig(id, spid) VALUES(%s, %s);",
                             (sensor_protocol_config["id"], sensor_protocol_config["spid"]))

    def create_sensor_protocol_config_parameters(self, sensor_protocol_config_parameters) -> None:
        for sensor_protocol_config_parameter in sensor_protocol_config_parameters:
            self.cur.execute(
                """
                INSERT INTO public.sensorprotocolconfigparameters(id, sensorprotocolconfigid, name, value)
                VALUES(%s, %s, %s, %s);
                """,
                (sensor_protocol_config_parameter["id"], sensor_protocol_config_parameter["sensorprotocolconfigid"],
                 sensor_protocol_config_parameter["name"], sensor_protocol_config_parameter["value"]))

    def create_qidmaps(self, qidmap_configs) -> None:
        for qidmap_config in qidmap_configs:
            self.cur.execute("INSERT INTO public.qidmap(id, qid) VALUES(%s, %s);",
                             (qidmap_config["id"], qidmap_config["qid"]))

    def create_dsm_events(self, dsm_event_configs) -> None:
        for dsm_event_config in dsm_event_configs:
            self.cur.execute(
                "INSERT INTO public.dsmevent(id, qidmapid, devicetypeid, deviceeventid) VALUES(%s, %s, %s, %s);",
                (dsm_event_config["id"], dsm_event_config["qidmapid"], dsm_event_config["devicetypeid"],
                 dsm_event_config["deviceeventid"]))

    def reset(self) -> None:
        self.cur.execute("DROP ROLE IF EXISTS qradar;")
        self.cur.execute("CREATE ROLE qradar WITH LOGIN SUPERUSER PASSWORD 'qradar';")
        self.cur.execute("DELETE FROM public.sensorprotocolconfigparameters;")
        self.cur.execute("DELETE FROM public.sensorprotocolconfig;")
        self.cur.execute("DELETE FROM public.domain_mapping;")
        self.cur.execute("DELETE FROM public.sensordevice;")
        self.cur.execute("DELETE FROM public.domains;")
        self.cur.execute("DELETE FROM public.dsmevent;")
        self.cur.execute("DELETE FROM public.qidmap;")

    def drop_qradar_user(self) -> None:
        self.cur.execute("DROP ROLE IF EXISTS qradar;")
