import psycopg2


class Database:

    def __init__(self) -> None:
        self.conn = psycopg2.connect("dbname='qradar' user='qradar'")

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
            self.cur.execute(
                "INSERT INTO public.domains(id, name) VALUES(%s, %s);",
                (domain["id"], domain["name"]))

    def create_sensor_devices(self, sensor_devices) -> None:
        for sensor_device in sensor_devices:
            self.cur.execute(
                """
            INSERT INTO
            public.sensordevice(id, hostname, devicename, devicetypeid, spconfig, timestamp_last_seen)
            VALUES(%s, %s, %s, %s, %s, extract(epoch from now())  * 1000);
            """, (sensor_device["id"], sensor_device["hostname"],
                  sensor_device["devicename"], sensor_device["devicetypeid"],
                  sensor_device["spconfig"]))

    def create_domain_mappings(self, domain_mappings) -> None:
        for domain_mapping in domain_mappings:
            self.cur.execute(
                "INSERT INTO public.domain_mapping(id, domain_id, source_type, source_id) VALUES(%s, %s, %s, %s);",
                (domain_mapping["id"], domain_mapping["domain_id"],
                 domain_mapping["source_type"], domain_mapping["source_id"]))

    def create_sensor_protocol_configs(self, sensor_protocol_configs) -> None:
        for sensor_protocol_config in sensor_protocol_configs:
            self.cur.execute(
                "INSERT INTO public.sensorprotocolconfig(id, spid) VALUES(%s, %s);",
                (sensor_protocol_config["id"], sensor_protocol_config["spid"]))

    def create_sensor_protocol_config_parameters(
            self, sensor_protocol_config_parameters) -> None:
        for sensor_protocol_config_parameter in sensor_protocol_config_parameters:
            self.cur.execute(
                """
                INSERT INTO public.sensorprotocolconfigparameters(id, sensorprotocolconfigid, name, value)
                VALUES(%s, %s, %s, %s);
                """,
                (sensor_protocol_config_parameter["id"],
                 sensor_protocol_config_parameter["sensorprotocolconfigid"],
                 sensor_protocol_config_parameter["name"],
                 sensor_protocol_config_parameter["value"]))

    def reset(self) -> None:
        self.cur.execute("DELETE FROM public.sensorprotocolconfigparameters;")
        self.cur.execute("DELETE FROM public.sensorprotocolconfig;")
        self.cur.execute("DELETE FROM public.domain_mapping;")
        self.cur.execute("DELETE FROM public.sensordevice;")
        self.cur.execute("DELETE FROM public.domains;")
