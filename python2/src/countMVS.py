#! /usr/bin/env python
"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import argparse
import csv
import logging
import warnings
import getpass
import os
import time
import sys
import socket
from socket import gaierror
import subprocess
import six
import requests
from requests.exceptions import RequestException
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import DatabaseError

# Disable insecure HTTPS warnings as most customers do not have
# certificate validation correctly configured for consoles
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# This is a hard-coded list of log source type IDs that are considered "not MVS"
# Future versions will be more comprehensive in what to exclude but for now this list is all we need to remove
LOG_SOURCE_EXCLUDE = [331, 352, 359, 361, 382, 405]

# This is a hard-coded map of sensor protocol type ids to the name
# of the protocol parameter that can be used as a unique identifier
SENSOR_PROTOCOL_MAP = {
    2: 'serverIp',
    7: 'url',
    8: 'databaseServerHostname',
    9: 'deviceAddress',
    15: 'remoteHost',
    16: 'SERVER_ADDRESS',
    17: 'SERVER_ADDRESS',
    18: 'SERVER_ADDRESS',
    19: 'serverAddress',
    20: 'databaseServerHostname',
    21: 'SERVER_ADDRESS',
    32: 'SERVER_ADDRESS',
    34: 'ESXIP',
    37: 'databaseServerHostname',
    42: 'databaseServerHostname',
    43: 'vcloudURL',
    54: 'loginUrl',
    55: 'databaseServerHostname',
    56: 'loginUrl',
    60: 'remoteHost',
    63: 'remoteHost',
    65: 'server',
    67: 'databaseServerHostname',
    68: 'hostname',
    69: 'server',
    74: 'tenantUrl',
    75: 'apiHostname',
    77: 'authorizationServerUrl',
    79: 'serverurl',
    83: 'endpointURL',
    84: 'hostname',
    87: 'loginEndPoint',
    90: 'authorizationEndPoint',
}

WINDOWS_SERVER_LOG_SOURCE_TYPES = {
    13: 'Microsoft IIS', 97: 'Microsoft DHCP', 98: 'Microsoft IAS', 99: 'Microsoft Exchange',
    101: 'Microsoft SQL Server', 191: 'Microsoft ISA'
}

MS_WINDOWS_SECURITY_EVENT_LOG_SOURCE_TYPE = 12

WINDOWS_SERVER_EVENT_IDS = [
    4768, 4727, 4728, 4729, 4730, 4737, 4744, 4745, 4746, 4747, 4748, 4749, 4750, 4751, 4752, 4753, 4754, 4755, 4756,
    4757, 4758, 4759, 4760, 4761, 4762, 4763, 4770, 4771, 4777
]


class RESTException(Exception):

    def __init__(self, message, api_error=None):
        self.message = message
        self.api_error = api_error
        super(RESTException, self).__init__(message)

    def __str__(self):
        return str(self.message)

    def get_api_error(self):
        return self.api_error


class ValidatorException(Exception):
    pass


class APIException(Exception):
    pass


class TooManyResultsError(Exception):
    pass


class LogSourceRetrievalException(Exception):
    pass


class DomainRetrievalException(Exception):
    pass


class WindowsWorkstationRetrievalException(Exception):
    pass


class MyVerException(Exception):
    pass


class QuitSelected(Exception):
    pass


class LogSource(object):

    # pylint: disable=too-many-arguments
    def __init__(self,
                 device_id=None,
                 hostname=None,
                 domains=None,
                 devicename=None,
                 devicetypeid=None,
                 spconfig=None,
                 timestamp_last_seen=None):
        self.sensor_device_id = device_id
        self.hostname = hostname
        self.device_name = devicename
        if domains:
            self.domains = domains
        else:
            self.domains = []
        self.device_type_id = devicetypeid
        self.sp_config = spconfig
        self.timestamp_last_seen = timestamp_last_seen

    def get_sensor_device_id(self):
        return self.sensor_device_id

    def set_sensor_device_id(self, sensor_device_id):
        self.sensor_device_id = sensor_device_id

    def get_hostname(self):
        return self.hostname

    def set_hostname(self, hostname):
        self.hostname = hostname

    def get_domains(self):
        return self.domains

    def add_domain(self, domain):
        if not domain in self.domains:
            self.domains.append(domain)

    def set_domains(self, domains):
        domains = list(dict.fromkeys(domains))
        self.domains = domains

    def get_first_domain(self):
        if not self.domains:
            return None
        return self.domains[0]

    def get_device_type_id(self):
        return self.device_type_id

    def set_device_type_id(self, device_type_id):
        self.device_type_id = device_type_id

    def get_sp_config(self):
        return self.sp_config

    def is_multi_domain(self):
        if self.domains:
            return len(self.domains) > 1
        return False

    @staticmethod
    def load_from_db_row(row):
        if row:
            object_keys = [
                'id', 'hostname', 'domains', 'devicename', 'devicetypeid', 'spconfig', 'timestamp_last_seen'
            ]
            device_id = 0
            for k in list(row.keys()):
                if k == 'id':
                    device_id = row[k]
                    del row[k]
                if not k in object_keys:
                    del row[k]
            row['device_id'] = device_id
            return LogSource(**row)
        return LogSource()


class LogSourceToDomainMapping(object):

    def __init__(self):
        self.logsource_to_domain = {}

    def add_mapping_from_json(self, response_json):
        if response_json and 'logsourceid' in response_json and 'domainname_domainid' in response_json:
            log_source_id = response_json['logsourceid']
            domain_name = response_json['domainname_domainid']
            if log_source_id in self.logsource_to_domain:
                self.logsource_to_domain[log_source_id].append(str(domain_name))
            else:
                self.logsource_to_domain[log_source_id] = [str(domain_name)]

    def get_logsource_to_domain(self):
        return self.logsource_to_domain

    def __str__(self):
        mappings = []
        for log_source_id, domains in self.logsource_to_domain.items():
            mapping = '{} : {}'.format(log_source_id, str(domains))
            mappings.append(mapping)

        return '[{}]'.format('\n'.join(mappings))


class ArielSearch(object):

    # pylint: disable=too-many-arguments
    def __init__(self, search_id=None, status=None, progress=0, completed=False, record_count=0):
        self.search_id = search_id
        self.status = status
        self.progress = progress
        self.completed = completed
        self.record_count = record_count

    def get_search_id(self):
        return self.search_id

    def get_status(self):
        return self.status

    def set_status(self, status):
        self.status = status

    def get_progress(self):
        return self.progress

    def set_progress(self, progress):
        self.progress = progress

    def is_completed(self):
        return self.completed

    def set_completed(self, completed):
        self.completed = completed

    def get_record_count(self):
        return self.record_count

    @staticmethod
    def from_json(response_json):
        if response_json:
            object_keys = ['search_id', 'status', 'progress', 'completed', 'record_count']
            for k in response_json.keys():
                if not k in object_keys:
                    del response_json[k]
            return ArielSearch(**response_json)
        return None


class APIError(object):

    def __init__(self, http_response=None, message=None):
        self.http_response = http_response
        self.detailed_error_message = message

    def get_response_code(self):
        if self.http_response and 'code' in self.http_response:
            return self.http_response['code']
        return None

    def set_response_code(self, code):
        if not self.http_response:
            self.http_response = {}
        self.http_response['code'] = code

    def get_error_message(self):
        if self.http_response and 'message' in self.http_response:
            return self.http_response['message']
        return None

    def set_error_message(self, message):
        if not self.http_response:
            self.http_response = {}
        self.http_response['message'] = message

    def get_detailed_error_message(self):
        return self.detailed_error_message

    def set_detailed_error_message(self, message):
        self.detailed_error_message = message

    @staticmethod
    def from_json(response_json):
        if response_json:
            object_keys = ['http_response', 'message']
            for k in response_json.keys():
                if not k in object_keys:
                    del response_json[k]
            return APIError(**response_json)
        return APIError()

    @staticmethod
    def from_response_status_and_text(response_status, response_text):
        return APIError({'code': response_status}, response_text)


class APIErrorGenerator(object):

    LOCKED_OUT_ERROR = ('Your host has been locked out due to too many failed login attempts. '
                        'Please try again later.')
    INCORRECT_PASSWORD = 'You have provided an incorrect password. '
    INCORRECT_TOKEN = 'You have provided an incorrect token. '
    INCORRECT_PERMISSIONS = 'The token provided has incorrect permissions. '
    RE_RUN_MESSAGE = 'Please re-run the script and try again.'
    LOCKED_OUT = 'locked out'
    PASSWORD_AUTH_ERROR = INCORRECT_PASSWORD + RE_RUN_MESSAGE
    TOKEN_AUTH_ERROR = INCORRECT_TOKEN + RE_RUN_MESSAGE
    TOKEN_PERMISSIONS_ERROR = INCORRECT_PERMISSIONS + RE_RUN_MESSAGE

    def __init__(self, client_auth, exception):
        self.client_auth = client_auth
        self.exception = exception
        self.response_code = None
        self.detailed_error_message = None
        self._init()

    def _init(self):
        if self.exception:
            if isinstance(self.exception, RESTException):
                api_error = self.exception.get_api_error()
                self.response_code = api_error.get_response_code()
                self.detailed_error_message = api_error.get_detailed_error_message()
            elif isinstance(self.exception, APIException):
                self.detailed_error_message = str(self.exception)

    def _generate_unauth_message(self):
        unauth_error_message = self.detailed_error_message
        if self.client_auth:
            if self.LOCKED_OUT in self.detailed_error_message:
                unauth_error_message = self.LOCKED_OUT_ERROR
            elif self.client_auth.password_authentication():
                unauth_error_message = self.PASSWORD_AUTH_ERROR
            elif self.client_auth.token_authentication():
                unauth_error_message = self.TOKEN_AUTH_ERROR
        return unauth_error_message

    def generate_error_message(self):
        error_message = self.detailed_error_message
        if self.response_code:
            if self.response_code == 401:
                error_message = self._generate_unauth_message()
            elif self.response_code == 403 and self.client_auth and self.client_auth.token_authentication():
                error_message = self.TOKEN_PERMISSIONS_ERROR
        return error_message


class PermissionCheckResult(object):

    def __init__(self, client_auth):
        self.client_auth = client_auth
        self.exception = None
        self.response_json = None

    def is_successful(self):
        return self.exception is None

    def set_exception(self, exception):
        self.exception = exception

    def get_response_json(self):
        return self.response_json

    def set_response_json(self, response_json):
        self.response_json = response_json

    def get_error_message(self):
        api_error_generator = APIErrorGenerator(self.client_auth, self.exception)
        return api_error_generator.generate_error_message()


class AQLClient(object):

    API_URL = '/api'
    ARIEL_API_URL = API_URL + '/ariel'
    ARIEL_SEARCHES_ENDPOINT = ARIEL_API_URL + '/searches'
    ARIEL_SEARCH_ENDPOINT = ARIEL_SEARCHES_ENDPOINT + '/{}'
    ARIEL_SEARCH_RESULTS_ENDPOINT = ARIEL_SEARCH_ENDPOINT + '/results'
    SYSTEM_ABOUT_TEST_ENDPOINT = API_URL + '/system/about'

    def __init__(self, rest_client):
        self.rest_client = rest_client

    def perform_search(self, query):
        params = {'query_expression': query}
        response_json = self.rest_client.post(path=self.ARIEL_SEARCHES_ENDPOINT, success_code=201, params=params)
        search = ArielSearch.from_json(response_json)
        return search

    def get_search(self, search_id):
        response_json = self.rest_client.get(path=self.ARIEL_SEARCH_ENDPOINT.format(search_id))
        search = ArielSearch.from_json(response_json)
        return search

    def get_search_result(self, search_id, headers=None):
        response_json = self.rest_client.get(path=self.ARIEL_SEARCH_RESULTS_ENDPOINT.format(search_id),
                                             headers=headers)
        if response_json and 'events' in response_json:
            return response_json['events']
        return []

    def check_api_permissions(self):
        # We are using the system about REST API endpoint here because the
        # ariel search endpoint returns an empty list when using an authorized service token
        # that does not have the ADMIN capability
        client_auth = self.rest_client.get_client_auth()
        permission_check_result = PermissionCheckResult(client_auth)
        try:
            response_json = self.rest_client.get(path=self.SYSTEM_ABOUT_TEST_ENDPOINT)
            permission_check_result.set_response_json(response_json)
        except (APIException, RESTException) as err:
            permission_check_result.set_exception(err)
        return permission_check_result


class RESTClient(object):

    SEC_HEADER = 'SEC'

    def __init__(self, hostname, insecure=False):
        self.hostname = hostname
        self.client_auth = None
        self.verify = not insecure

    def set_client_auth(self, client_auth):
        self.client_auth = client_auth

    def get_client_auth(self):
        return self.client_auth

    def get(self, path, success_code=200, headers=None):
        try:
            rest_headers = self._build_headers(headers)
            response = requests.get(self._build_url(path),
                                    headers=rest_headers,
                                    auth=self._build_auth(),
                                    verify=self.verify)
        except (RequestException, ValueError) as err:
            raise APIException(err)

        if response.status_code == 404:
            return None
        if response.status_code == success_code:
            return response.json()

        try:
            api_error = APIError.from_json(response.json())
        except ValueError:
            api_error = APIError.from_response_status_and_text(response.status_code, response.text)
        raise RESTException(api_error.get_error_message(), api_error)

    def post(self, path, success_code=200, params=None, headers=None):
        try:
            rest_headers = self._build_headers(headers)
            response = requests.post(self._build_url(path),
                                     headers=rest_headers,
                                     params=params,
                                     auth=self._build_auth(),
                                     verify=self.verify)
        except (RequestException, ValueError) as err:
            raise APIException(err)

        if response.status_code == 404:
            return None
        if response.status_code == success_code:
            return response.json()

        try:
            api_error = APIError.from_json(response.json())
        except ValueError:
            api_error = APIError.from_response_status_and_text(response.status_code, response.text)
        raise RESTException(api_error.get_error_message(), api_error)

    def _build_headers(self, headers):
        if headers is None:
            headers = {}
        if self.client_auth and self.client_auth.get_auth_services_token():
            headers[self.SEC_HEADER] = self.client_auth.get_auth_services_token()
        return headers

    def _build_auth(self):
        if self.client_auth and self.client_auth.get_username() and self.client_auth.get_password():
            return (self.client_auth.get_username(), self.client_auth.get_password())
        return None

    def _build_url(self, path):
        return "https://{}{}".format(self.hostname, path)


class DatabaseClient(object):

    TOO_MANY_ROWS_ERROR_MESSAGE = 'Too many rows returned'

    def __init__(self, dbname=None, username=None):
        self.dbname = dbname
        self.username = username
        self.conn = None

    def connect(self):
        self.conn = psycopg2.connect(database=self.dbname, user=self.username, cursor_factory=RealDictCursor)

    def fetch_one(self, sql):
        with self.conn.cursor() as cursor:
            cursor.execute(sql)
            if cursor.rowcount > 1:
                raise TooManyResultsError(self.TOO_MANY_ROWS_ERROR_MESSAGE)
            return cursor.fetchone()

    def fetch_all(self, sql):
        with self.conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    def close(self):
        if self.conn:
            self.conn.close()


class MachineIdentifierParser(object):

    @staticmethod
    def parse_machine_identifier(machine_id):
        # If value is a url we need to retrieve the hostname/IP to use as identifier
        if '//' in machine_id:
            # remove substring before double slash
            machine_id = machine_id.split('//', 1)[1]
            # remove substring after next slash, if exists
            machine_id = machine_id.split('/', 1)[0]
            # remove substring after next colon, if exists
            machine_id = machine_id.split(':', 1)[0]
        return machine_id


class DatabaseService(object):

    LOG_SOURCE_RETRIEVAL_QUERY = ('SELECT id, hostname, devicename, devicetypeid, spconfig, timestamp_last_seen '
                                  'FROM sensordevice '
                                  'WHERE timestamp_last_seen > {} and spconfig is not null')
    SENSOR_PROTOCOL_ID_QUERY = ('SELECT spid '
                                'FROM sensorprotocolconfig '
                                'WHERE id = {}')
    CONFIG_PARAM_VALUE_QUERY = ('SELECT value '
                                'FROM sensorprotocolconfigparameters '
                                'WHERE sensorprotocolconfigid = {} and name = \'{}\'')
    DOMAIN_COUNT_QUERY = ('SELECT COUNT(id) '
                          'FROM domains '
                          'WHERE deleted=false')
    WINDOWS_SERVER_QIDS_QUERY = ('SELECT qid '
                                 'FROM qidmap '
                                 'WHERE id IN (SELECT qidmapid '
                                 'FROM dsmevent '
                                 'WHERE devicetypeid = {} '
                                 'AND deviceeventid in ({}))')
    EXECUTING_QUERY_TEMPLATE = 'Executing query %s'

    def __init__(self, db_client):
        self.db_client = db_client

    def _execute_log_source_query(self, time_period):
        log_source_retrieval_query = self.LOG_SOURCE_RETRIEVAL_QUERY.format(time_period)
        logging.debug(self.EXECUTING_QUERY_TEMPLATE, log_source_retrieval_query)
        return self.db_client.fetch_all(log_source_retrieval_query)

    @staticmethod
    def _add_log_source_to_map(row, log_source_map):
        log_source = LogSource.load_from_db_row(row)
        log_source_id = log_source.get_sensor_device_id()
        logging.info('Adding log source %d to log source map', int(log_source_id))
        log_source_map[log_source_id] = log_source

    def build_log_source_map(self, time_period):
        logging.info('Attempting to build log source map from entries in the database')
        error_message_template = 'Unable to retrieve log sources ' \
                                 'from the database, Reason [{}]'
        try:
            log_source_map = {}
            rows = self._execute_log_source_query(time_period)
            logging.info('Query executed successfully, %d rows returned', len(rows))
            for row in rows:
                self._add_log_source_to_map(row, log_source_map)
            return log_source_map
        except (DatabaseError, TooManyResultsError) as err:
            raise LogSourceRetrievalException(error_message_template.format(err))

    def _get_sensor_protocol_id(self, log_source):
        sp_id = None
        sp_id_query = self.SENSOR_PROTOCOL_ID_QUERY.format(log_source.get_sp_config())
        logging.debug(self.EXECUTING_QUERY_TEMPLATE, sp_id_query)
        sp_id_query_result = self.db_client.fetch_one(sp_id_query)
        if sp_id_query_result and 'spid' in sp_id_query_result:
            sp_id = sp_id_query_result['spid']
            logging.debug('Query executed successfully. Retrieved spid=%s', sp_id)
        else:
            logging.debug('No results found for spid for id %s', log_source.get_sp_config())
        return sp_id

    def _get_sensor_config_param_value(self, param_name, log_source):
        value = None
        # This log source uses a protocol parameter as its identifier, retrieve name of
        # parameter from SENSOR_PROTOCOL_MAP then retrieve value from postgres
        config_param_query = self.CONFIG_PARAM_VALUE_QUERY.format(log_source.get_sp_config(), param_name)
        logging.debug(self.EXECUTING_QUERY_TEMPLATE, config_param_query)
        config_param_query_result = self.db_client.fetch_one(config_param_query)
        if config_param_query_result and 'value' in config_param_query_result:
            value = config_param_query_result['value']
            logging.debug("Query executed successfully. Retrieved value = %s", value)
        else:
            logging.debug('No results found for parameter name %s', param_name)
        return value

    def _parse_machine_identifier(self, sp_id, log_source, machine_id):
        if sp_id in SENSOR_PROTOCOL_MAP:
            param_name = SENSOR_PROTOCOL_MAP[sp_id]
            if param_name:
                param_value = self._get_sensor_config_param_value(param_name, log_source)
                if param_value:
                    machine_id = MachineIdentifierParser.parse_machine_identifier(param_value)
        return machine_id

    # Determine a unique identifier for this log source
    def get_machine_identifier(self, log_source):
        error_message = 'Unable to retrieve machine identifier'
        # If machine is not a special case then the
        # default identifier is the hostname
        machine_id = log_source.get_hostname()
        try:
            sp_id = self._get_sensor_protocol_id(log_source)
            if sp_id and sp_id in SENSOR_PROTOCOL_MAP:
                machine_id = self._parse_machine_identifier(sp_id, log_source, machine_id)
        except (DatabaseError, TooManyResultsError) as err:
            logging.error('%s using hostname instead, '\
                          'Reason [%s]', error_message, err)
        return machine_id

    def get_domain_count(self):
        error_message_template = 'Unable to retrieve domain count from the database, {}'
        try:
            domain_count_query_result = self.db_client.fetch_one(self.DOMAIN_COUNT_QUERY)
            if domain_count_query_result:
                return int(domain_count_query_result['count'])
            domain_query_failure = 'No result returned when executing query {}'.format(self.DOMAIN_COUNT_QUERY)
            raise DomainRetrievalException(error_message_template.format(domain_query_failure))
        except (DatabaseError, TooManyResultsError) as err:
            raise DomainRetrievalException(error_message_template.format(err))

    def get_windows_server_qids(self):
        qids = []
        event_ids = ','.join("'{}'".format(event_id) for event_id in WINDOWS_SERVER_EVENT_IDS)
        windows_server_qids_query = self.WINDOWS_SERVER_QIDS_QUERY.format(MS_WINDOWS_SECURITY_EVENT_LOG_SOURCE_TYPE,
                                                                          event_ids)
        logging.debug(self.EXECUTING_QUERY_TEMPLATE, windows_server_qids_query)
        rows = self.db_client.fetch_all(windows_server_qids_query)
        for row in rows:
            qids.append(row['qid'])
        return qids


class Auth(object):

    def __init__(self):
        self.username = 'admin'
        self.password = None
        self.auth_services_token = None
        self.password_auth = False
        self.token_auth = False

    def get_username(self):
        return self.username

    def get_password(self):
        return self.password

    def set_password(self, password):
        self.password = password
        self.password_auth = True

    def get_auth_services_token(self):
        return self.auth_services_token

    def set_auth_services_token(self, token):
        self.auth_services_token = token
        self.token_auth = True

    def password_authentication(self):
        return self.password_auth

    def token_authentication(self):
        return self.token_auth


class TextFormatter(object):

    BOLD_ANSI_ESCAPE_CODE = '\033[1m'
    NORMAL_ANSI_ESCAPE_CODE = '\033[0m'

    @staticmethod
    def bold(text_to_format):
        return '{}{}{}'.format(TextFormatter.BOLD_ANSI_ESCAPE_CODE, text_to_format,
                               TextFormatter.NORMAL_ANSI_ESCAPE_CODE)


class TimePeriodReader(object):

    @staticmethod
    def _print_description_header(default_period_in_days):
        formatter = TextFormatter()
        print('\nThis script calculates an estimated count of the MVS (Managed Virtual Servers) for the deployment.')
        print(
            'It uses log source data in order to calculate the count over a given time period. By default the script')
        print('will use {} days worth of log source data however you can select to increase this below.\n'.format(
            default_period_in_days))
        print(
            formatter.bold('Note') +
            ': By increasing the value from the default {} day(s) this will increase the execution time of the script'.
            format(default_period_in_days))
        print('especially in multi-domain deployments as it will have to perform a search for log source data over a ')
        print('longer period of time.\n')
        print('How many days worth of log source data would you like to use for the calculation.\n')

    @staticmethod
    def prompt_for_time_period(default_period_in_days, max_period_in_days):
        TimePeriodReader._print_description_header(default_period_in_days)
        period_in_days = default_period_in_days
        while True:
            try:
                response = six.moves.input('Please enter your choice in days (default {} [Enter], max {}): '.format(
                    default_period_in_days, max_period_in_days))
                if not response:
                    break
                period_in_days = int(response)
                if period_in_days >= 1 and period_in_days <= max_period_in_days:
                    break
                if period_in_days < 1:
                    print('Invalid selection. You can only select a minimum of 1 day')
                if period_in_days > max_period_in_days:
                    print(
                        'Invalid selection. You can only select up to a maximum of {} days'.format(max_period_in_days))

            except ValueError:
                print('Invalid selection. You must enter a numeric value')
        return period_in_days


class AuthReader(object):

    @staticmethod
    def prompt_for_auth_method():
        client_auth = Auth()
        print('\nThis script needs to call the Ariel API to calculate the MVS count from the deployment.\n\n'
              'Which authentication would you like to use:\n1: Admin User\n2: Authorized Service\n'
              '(q to quit)\n')
        while True:
            auth_choice = str(six.moves.input('Please enter your choice: '))
            if auth_choice == '1':
                client_auth.set_password(getpass.getpass('Please input the admin user password: '))
                break
            if auth_choice == '2':
                client_auth.set_auth_services_token(
                    getpass.getpass('Please input the security token for your authorized service: '))
                break
            if auth_choice in ('q', 'Q'):
                client_auth = None
                break
            print('\nInvalid selection. Please choose from the following options:'
                  '\n1. Admin User\n2. Authorized Service\n(q to quit)\n')
        return client_auth


class ProgressUtils(object):

    @staticmethod
    def _resolve_invalid_progress_range(progress):
        if progress is None or progress < 0:
            progress = 0
        elif progress > 100:
            progress = 100
        return progress

    @staticmethod
    def print_progress_bar(progress):
        progress = ProgressUtils._resolve_invalid_progress_range(progress)
        progress_bar_length = int(progress / 2)
        search_status = '{}%'.format(progress)
        sys.stdout.write('\rProcessing... |' + '#' * progress_bar_length + '-' * (50 - progress_bar_length) + '| ' +
                         search_status)
        sys.stdout.flush()
        if progress == 100:
            complete_msg = '100% ...done\n\n'
            sys.stdout.write('\rProcessing... |' + '#' * progress_bar_length + '-' * (50 - progress_bar_length) +
                             '| ' + complete_msg)
            sys.stdout.flush()


class DomainAppender(object):

    DEFAULT_DOMAIN = 'Default Domain'
    DOMAIN_AQL_QUERY_TEMPLATE = ('SELECT logsourceid,DOMAINNAME(domainid) '
                                 'FROM events GROUP BY logsourceid,domainid '
                                 'ORDER BY logsourceid LAST {} DAYS')
    MAX_SEARCH_RESULTS_PER_REQUEST = 49

    def __init__(self, multi_domain, aql_client=None, period_in_days=1):
        self.multi_domain = multi_domain
        self.aql_client = aql_client
        self.period_in_days = period_in_days
        self.ariel_search = None
        self.range_start = 0
        self.range_end = self.MAX_SEARCH_RESULTS_PER_REQUEST

    def _add_default_domain(self, log_source_map):
        for log_source in log_source_map.values():
            log_source.add_domain(self.DEFAULT_DOMAIN)

    def _perform_aql_query(self):
        print('\nPerforming AQL query to retrieve log source domain information, '
              'Please wait...')
        domain_aql_query = self.DOMAIN_AQL_QUERY_TEMPLATE.format(self.period_in_days)
        logging.debug('Attempting to execute AQL query %s', domain_aql_query)
        return self.aql_client.perform_search(domain_aql_query)

    def _poll_query_for_completion(self):
        logging.info('Polling for completion of ariel search with id %s', self.ariel_search.get_search_id())
        while not self.ariel_search.is_completed():
            current_ariel_search = self.aql_client.get_search(self.ariel_search.get_search_id())
            if current_ariel_search:
                self.ariel_search = current_ariel_search
                logging.info('Ariel search with id %s has status %s', self.ariel_search.get_search_id(),
                             self.ariel_search.get_status())
                ProgressUtils.print_progress_bar(self.ariel_search.get_progress())
                time.sleep(1)
        logging.info('Ariel search with id %s completed', self.ariel_search.get_search_id())

    def _build_mapping_from_results(self):
        # Retrieve results for the AQL query
        mapping = LogSourceToDomainMapping()
        range_headers = self._build_range_header()
        while range_headers:
            search_results = self.aql_client.get_search_result(self.ariel_search.get_search_id(), range_headers)
            if search_results is not None:
                for search_result in search_results:
                    mapping.add_mapping_from_json(search_result)
                self.range_start = self.range_end + 1
                self.range_end = self.range_start + self.MAX_SEARCH_RESULTS_PER_REQUEST
                range_headers = self._build_range_header()
            else:
                logging.debug('No search results returned from Ariel API search')
        logging.debug('Mapping result %s', str(mapping))
        return mapping.get_logsource_to_domain()

    def _build_range_header(self):
        if self.range_start > self.ariel_search.get_record_count():
            return None
        headers = {}
        last_item = self.range_end
        if self.range_end >= self.ariel_search.get_record_count():
            last_item = self.ariel_search.get_record_count() - 1
        headers['Range'] = 'items={}-{}'.format(str(self.range_start), str(last_item))
        return headers

    def _build_logsource_to_domain_map(self):
        error_message_template = 'Unable to retrieve domain information. ERROR {}'
        try:
            # Call API to perform an AQL search for log sources with
            # associated domain names for the specified time period (1 day by default)
            self.ariel_search = self._perform_aql_query()
            if not self.ariel_search:
                error_message = 'POST to ariel API returned a 404'
                raise DomainRetrievalException(error_message_template.format(error_message))
            # Poll for completion of the AQL search using the API
            self._poll_query_for_completion()
            if self.ariel_search.get_status() in ['ERROR', 'CANCELED']:
                status_failure = 'Ariel search did not complete ' \
                                 'successfully, status is {}'.format(self.ariel_search.get_status())
                raise DomainRetrievalException(error_message_template.format(status_failure))
            return self._build_mapping_from_results()
        except (APIException, RESTException) as err:
            raise DomainRetrievalException(error_message_template.format(err))

    def add_domains(self, log_source_map):
        if self.multi_domain:
            logsource_to_domain_mapping = self._build_logsource_to_domain_map()
            for logsource_id, domains in logsource_to_domain_mapping.items():
                if logsource_id in log_source_map:
                    logging.info('Appending domain information for log source id %d', logsource_id)
                    log_source = log_source_map[logsource_id]
                    log_source.set_domains(domains)
        else:
            logging.info('Appending default domain to all log sources')
            self._add_default_domain(log_source_map)
        logging.info('Completed adding domain information to log sources')


class WindowsDeviceProcessor(object):

    WINDOWS_SERVER_QUERY_TEMPLATE = ('SELECT qid '
                                     'FROM events '
                                     'WHERE logsourceid IN ({}) '
                                     'AND qid IN ({}) LIMIT 1 LAST {} DAYS')
    WINDOWS_WORKSTATION_CACHE_FILE = '.windows_workstations'

    def __init__(self, aql_client, db_service, mvs_results, period_in_days=1):
        self.aql_client = aql_client
        self.db_service = db_service
        self.mvs_results = mvs_results
        self.period_in_days = period_in_days
        self.cached_windows_workstations = []
        self.windows_workstations = []
        self.ariel_search = None

    def _perform_aql_query(self, machine_identifier, log_source_ids):
        print('\nPerforming AQL query to check if {} is a windows server or workstation, '
              'Please wait...'.format(machine_identifier))
        windows_server_qids = self.db_service.get_windows_server_qids()
        ls_ids = ','.join("{}".format(ls_id) for ls_id in log_source_ids)
        qids = ','.join("{}".format(qid) for qid in windows_server_qids)
        windows_server_aql_query = self.WINDOWS_SERVER_QUERY_TEMPLATE.format(ls_ids, qids, self.period_in_days)
        logging.debug('Attempting to execute AQL query %s', windows_server_aql_query)
        return self.aql_client.perform_search(windows_server_aql_query)

    def _poll_query_for_completion(self):
        logging.info('Polling for completion of search with id %s', self.ariel_search.get_search_id())
        while not self.ariel_search.is_completed():
            current_ariel_search = self.aql_client.get_search(self.ariel_search.get_search_id())
            if current_ariel_search:
                self.ariel_search = current_ariel_search
                logging.info('Ariel search with id %s has status %s', self.ariel_search.get_search_id(),
                             self.ariel_search.get_status())
                ProgressUtils.print_progress_bar(self.ariel_search.get_progress())
                time.sleep(1)
        logging.info('Ariel search with id %s completed', self.ariel_search.get_search_id())

    def _get_result_count(self):
        error_message_template = 'Unable to retrieve windows workstation query result. ERROR {}'
        error_message = 'No ariel search result found for {}'.format(self.ariel_search.get_search_id())
        search_results = self.aql_client.get_search_result(self.ariel_search.get_search_id())
        if search_results is not None:
            return len(search_results)
        else:
            raise WindowsWorkstationRetrievalException(error_message_template.format(error_message))

    def get_windows_workstations(self):
        return self.windows_workstations

    def _read_machine_identifiers_from_cache(self):
        if os.path.exists(self.WINDOWS_WORKSTATION_CACHE_FILE):
            with open(self.WINDOWS_WORKSTATION_CACHE_FILE) as cache_file:
                self.cached_windows_workstations = cache_file.read().splitlines()

    def _store_machine_identifier(self, machine_identifier):
        with open(self.WINDOWS_WORKSTATION_CACHE_FILE, 'a') as cache_file:
            cache_file.write(machine_identifier + '\n')

    def _perform_windows_workstation_check(self, machine_identifier, windows_sec_event_log_source_ids):
        error_message_template = 'Unable to perform windows workstation check. ERROR {}'
        logging.info('Performing workstation check on %s', machine_identifier)
        try:
            self.ariel_search = self._perform_aql_query(machine_identifier, windows_sec_event_log_source_ids)
            if self.ariel_search:
                self._poll_query_for_completion()
                result_count = self._get_result_count()
                logging.info('Event result count was %d for %s', result_count, machine_identifier)
                if result_count == 0:
                    logging.debug('Result count was 0 for machine identifier %s', machine_identifier)
                    self.windows_workstations.append(machine_identifier)
                    if machine_identifier not in self.cached_windows_workstations:
                        self._store_machine_identifier(machine_identifier)
            else:
                error_message = 'POST to ariel API returned a 404'
                raise WindowsWorkstationRetrievalException(error_message_template.format(error_message))
        except (APIException, RESTException) as err:
            raise WindowsWorkstationRetrievalException(error_message_template.format(err))

    def _perform_windows_server_log_sources_check(self, machine_identifier, log_sources):
        windows_sec_event_log_source_ids = []
        windows_server = False
        for log_source in log_sources:
            if log_source.get_device_type_id() == MS_WINDOWS_SECURITY_EVENT_LOG_SOURCE_TYPE:
                logging.info('Found windows workstation log source associated with machine identifier %s, '\
                             'storing log source %d for further processing',
                             machine_identifier, log_source.get_sensor_device_id())
                windows_sec_event_log_source_ids.append(log_source.get_sensor_device_id())
            if log_source.get_device_type_id() in WINDOWS_SERVER_LOG_SOURCE_TYPES:
                logging.info('Log source %d associated with machine identifier %s is a windows server',
                             log_source.get_sensor_device_id(), machine_identifier)
                windows_server = True
                break
        if not windows_server and windows_sec_event_log_source_ids:
            self._perform_windows_workstation_check(machine_identifier, windows_sec_event_log_source_ids)

    def process_devices(self):
        self._read_machine_identifiers_from_cache()
        for machine_identifier, log_sources in self.mvs_results.get_device_map().items():
            if machine_identifier in self.cached_windows_workstations:
                logging.info('Machine identifier %s was found in the windows workstation cache, skipping ariel search',
                             machine_identifier)
                self.windows_workstations.append(machine_identifier)
                continue
            self._perform_windows_server_log_sources_check(machine_identifier, log_sources)


class IPParser(object):

    @staticmethod
    def get_device_ip(hostname):
        try:
            return socket.gethostbyname(hostname)
        except gaierror as err:
            logging.error('Unable to resolve hostname %s to IP, ' \
                          'Reason [%s]', hostname, str(err))
            return None


class MVSResults(object):

    def __init__(self):
        self.device_map = {}
        self.domain_count_map = {}
        self.mvs_count = 0
        self.excluded_log_sources = []
        self.skipped_log_sources = []
        self.windows_workstation_device_map = {}
        self.log_source_count = 0

    def set_device_map(self, device_map):
        self.device_map = device_map

    def set_domain_count_map(self, domain_count_map):
        self.domain_count_map = domain_count_map

    def set_mvs_count(self, mvs_count):
        self.mvs_count = mvs_count

    def set_log_source_count(self, log_source_count):
        self.log_source_count = log_source_count

    def get_device_map(self):
        return self.device_map

    def get_domain_count_map(self):
        return self.domain_count_map

    def get_mvs_count(self):
        return self.mvs_count

    def get_excluded_log_sources(self):
        return self.excluded_log_sources

    def get_skipped_log_sources(self):
        return self.skipped_log_sources

    def get_windows_workstation_device_map(self):
        return self.windows_workstation_device_map

    def get_log_source_count(self):
        return self.log_source_count

    def get_excluded_log_source_count(self):
        return len(self.excluded_log_sources) + len(self.windows_workstation_device_map.values())

    def add_excluded_log_source(self, log_source):
        self.excluded_log_sources.append(log_source)

    def add_skipped_log_source(self, log_source):
        self.skipped_log_sources.append(log_source)

    def add_windows_workstation(self, machine_identifier, log_sources):
        self.windows_workstation_device_map[machine_identifier] = log_sources

    def increment_mvs_count(self):
        self.mvs_count += 1


class LogSourceProcessor(object):

    def __init__(self, db_service, aql_client, multi_domain=False):
        self.db_service = db_service
        self.aql_client = aql_client
        self.multi_domain = multi_domain
        self.mvs_results = MVSResults()
        self.multidomain_device_list = []
        self.additions = {}
        self.removals = []

    def _update_multidomain_list(self, device_ip, machine_identifier):
        if device_ip not in self.multidomain_device_list:
            logging.debug('Adding device_ip %s to multidomain_device_list', device_ip)
            self.multidomain_device_list.append(device_ip)
        if machine_identifier in self.multidomain_device_list:
            logging.debug('Removing machine_identifier %s from multidomain_device_list', machine_identifier)
            self.multidomain_device_list.remove(machine_identifier)

    def _add_to_additions_map(self, device_ip, log_sources):
        if device_ip not in self.additions:
            self.additions[device_ip] = log_sources
        else:
            self.additions[device_ip].extend(log_sources)

    def _consolidate_device_map(self, device_ip, machine_identifier, log_sources):
        if device_ip in self.mvs_results.get_device_map():
            logging.debug('Device ip %s is already present in device map, '\
                          'appending log sources to this IP', device_ip)
            self.mvs_results.get_device_map()[device_ip].extend(log_sources)
        else:
            logging.debug('Adding device ip %s to additions map', device_ip)
            self._add_to_additions_map(device_ip, log_sources)
        logging.debug('Adding machine identifier %s to removals list', machine_identifier)
        self.removals.append(machine_identifier)
        self._update_multidomain_list(device_ip, machine_identifier)

    def _update_device_map(self):
        self.mvs_results.get_device_map().update(self.additions)
        for machine_identifier in self.removals:
            del self.mvs_results.get_device_map()[machine_identifier]

    # pylint: disable=too-many-arguments
    def _resolve_hostnames_to_ips(self):
        logging.info('Attempting to resolve hostnames to ips')
        for machine_identifier, log_sources in self.mvs_results.get_device_map().items():
            logging.info('Attempting to resolve machine identifier %s to an ip address', machine_identifier)
            try:
                device_ip = IPParser.get_device_ip(machine_identifier)
            except Exception as err:
                logging.info('Unable to resolve machine identifier %s to an ip address', machine_identifier, str(err))
                continue
            if device_ip != machine_identifier:
                logging.info('Resolved machine identifer %s to ip address %s', machine_identifier, device_ip)
                self._consolidate_device_map(device_ip, machine_identifier, log_sources)
        self._update_device_map()

    def _update_count(self, domain):
        self.mvs_results.increment_mvs_count()
        if domain in self.mvs_results.get_domain_count_map():
            self.mvs_results.get_domain_count_map()[domain] += 1
        else:
            self.mvs_results.get_domain_count_map()[domain] = 1

    def _process_multi_domain_device(self, machine_identifier, log_sources):
        # Need to build a list of all domains for this machine identifier
        domains = []
        for log_source in log_sources:
            if not domains:
                domains = log_source.get_domains()
            else:
                union = list(set(domains) | set(log_source.get_domains()))
                domains = union
        logging.info("Machine Identifier %s is associated with domains %s", machine_identifier, str(domains))
        for domain in domains:
            self._update_count(domain)

    def _process_single_domain_device(self, machine_identifier, log_sources):
        # This machine identifier is not associated with multiple domains
        # therefore it counts as one MVS
        if log_sources:
            log_source = log_sources[0]
            domain = None
            if log_source:
                domain = log_source.get_first_domain()
                logging.info('Machine Identifier %s is associated with domain %s', machine_identifier, domain)
            if domain:
                self._update_count(domain)

    # In a system with log sources that have multiple domains we can't just count the number of IP/hostname(s)
    # We need to count each separate domain listed under an IP/hostname as a separate MVS
    def _process_domain_devices(self):
        for machine_identifier, log_sources in self.mvs_results.get_device_map().items():
            if machine_identifier in self.multidomain_device_list:
                self._process_multi_domain_device(machine_identifier, log_sources)
            else:
                self._process_single_domain_device(machine_identifier, log_sources)

    def _add_to_device_map(self, machine_identifier, log_source):
        if machine_identifier in self.mvs_results.get_device_map():
            self.mvs_results.get_device_map()[machine_identifier].append(log_source)
        else:
            self.mvs_results.get_device_map()[machine_identifier] = [log_source]

    def _process_log_source(self, log_source):
        if log_source.get_device_type_id() in LOG_SOURCE_EXCLUDE:
            self.mvs_results.add_excluded_log_source(log_source)
            logging.info('Device type id %s is in LOG_SOURCE_EXCLUDE, skipping...', log_source.get_device_type_id())
            return
        if not log_source.get_domains():
            self.mvs_results.add_skipped_log_source(log_source)
            logging.error('Log source with id %d has no domains, skipping...', log_source.get_sensor_device_id())
            return
        machine_identifier = self.db_service.get_machine_identifier(log_source)
        # If this log source has multiple domains then keep track of this IP as it will
        # require extra processing during the count
        if log_source.is_multi_domain():
            self.multidomain_device_list.append(machine_identifier)
        self._add_to_device_map(machine_identifier, log_source)

    def _remove_windows_workstations(self, period_in_days):
        windows_device_processor = WindowsDeviceProcessor(self.aql_client, self.db_service, self.mvs_results,
                                                          period_in_days)
        windows_device_processor.process_devices()
        windows_workstations = windows_device_processor.get_windows_workstations()
        for windows_workstation in windows_workstations:
            logging.info('Removing machine identifier %s from device map as its a windows workstation',
                         windows_workstation)
            log_sources = self.mvs_results.get_device_map()[windows_workstation]
            self.mvs_results.add_windows_workstation(windows_workstation, log_sources)
            del self.mvs_results.get_device_map()[windows_workstation]

    def process_log_sources(self, log_sources, period_in_days=1):
        self.mvs_results.set_log_source_count(len(log_sources))
        for log_source in log_sources:
            self._process_log_source(log_source)
        self._resolve_hostnames_to_ips()
        self._remove_windows_workstations(period_in_days)
        if self.multi_domain:
            self._process_domain_devices()
        else:
            self.mvs_results.set_mvs_count(len(self.mvs_results.get_device_map()))

    def get_mvs_results(self):
        return self.mvs_results


class ResultsGenerator(object):

    LOG_SOURCE_COLUMN_ORDER = [
        'sensor_device_id', 'device_name', 'hostname', 'device_type_id', 'timestamp_last_seen', 'sp_config', 'domains'
    ]
    LOG_SOURCE_COLUMN_NAMES = ['ID', 'Name', 'Log Source Identifier', 'Type ID', 'Last Seen', 'SP Config', 'Domains']

    def __init__(self, mvs_results, period_in_days):
        self.mvs_results = mvs_results
        self.period_in_days = period_in_days

    @staticmethod
    def add_blank_row(csv_file):
        csv_file.write('\n\n')

    @staticmethod
    def add_carriage_return(csv_file):
        csv_file.write('\n')

    def _write_domain_count_summary(self, csv_file):
        if self.mvs_results.get_domain_count_map():
            self.add_blank_row(csv_file)
            csv_file.write('MVS Count By Domain:\n')
            domains = list(self.mvs_results.get_domain_count_map().keys())
            domains.sort()
            csv_file.write('Domain Name, MVS Count\n')
            for domain in domains:
                csv_file.write('{},{}\n'.format(domain, self.mvs_results.get_domain_count_map()[domain]))

    def _write_mvs_count_summary(self, csv_file):
        csv_file.write('Results Summary:\n')
        csv_file.write('MVS Count = {}\n'.format(self.mvs_results.get_mvs_count()))
        csv_file.write('Data Period In Days = {}\n'.format(self.period_in_days))
        csv_file.write('Log Sources Processed = {}\n'.format(self.mvs_results.get_log_source_count()))
        csv_file.write('Log Sources Skipped = {}\n'.format(len(self.mvs_results.get_skipped_log_sources())))
        csv_file.write('Log Sources Excluded = {}'.format(self.mvs_results.get_excluded_log_source_count()))

    def _write_mvs_device_list(self, csv_file):
        csv_file.write('MVS List:\n')
        index = 0
        for machine_identifier in self.mvs_results.get_device_map().keys():
            csv_file.write(str(machine_identifier))
            if index < len(self.mvs_results.get_device_map().keys()) - 1:
                self.add_carriage_return(csv_file)
            index += 1

    def _write_excluded_log_source_details(self, csv_file, writer):
        if self.mvs_results.get_excluded_log_source_count() > 0:
            self.add_carriage_return(csv_file)
            csv_file.write('Excluded Log Source Details:\n')
            self._write_windows_workstation_list(csv_file, writer)
            self._write_excluded_log_sources(csv_file, writer)

    def _write_log_sources(self, csv_file, writer, log_sources):
        csv_file.write(','.join(self.LOG_SOURCE_COLUMN_NAMES) + '\n')
        for log_source in log_sources:
            writer.writerow(vars(log_source))

    def _write_windows_workstation_list(self, csv_file, writer):
        if self.mvs_results.get_windows_workstation_device_map():
            csv_file.write('Windows Workstations:\n')
            for machine_identifier, log_sources in self.mvs_results.get_windows_workstation_device_map().items():
                csv_file.write('MVS Device Id = {}\n'.format(machine_identifier))
                self._write_log_sources(csv_file, writer, log_sources)
                if machine_identifier != self.mvs_results.get_windows_workstation_device_map().keys()[-1]:
                    self.add_carriage_return(csv_file)

    def _write_excluded_log_sources(self, csv_file, writer):
        if self.mvs_results.get_excluded_log_sources():
            if self.mvs_results.get_windows_workstation_device_map():
                self.add_carriage_return(csv_file)
            csv_file.write('Non MVS Log Sources:\n')
            self._write_log_sources(csv_file, writer, self.mvs_results.get_excluded_log_sources())

    def _write_skipped_log_source_details(self, csv_file, writer):
        if self.mvs_results.get_skipped_log_sources():
            if self.mvs_results.get_excluded_log_source_count() > 0:
                self.add_carriage_return(csv_file)
            csv_file.write('Skipped Log Source Details:\n')
            self._write_log_sources(csv_file, writer, self.mvs_results.get_skipped_log_sources())

    def _write_mvs_log_source_details(self, csv_file, writer):
        csv_file.write('Log Source Details:\n')
        index = 0
        for machine_identifier, log_sources in self.mvs_results.get_device_map().items():
            csv_file.write('MVS Device Id = {}\n'.format(machine_identifier))
            self._write_log_sources(csv_file, writer, log_sources)
            if index < len(self.mvs_results.get_device_map().keys()) - 1:
                self.add_carriage_return(csv_file)
            index += 1

    def _write_log_source_details(self, csv_file, writer):
        self._write_mvs_log_source_details(csv_file, writer)
        self._write_excluded_log_source_details(csv_file, writer)
        self._write_skipped_log_source_details(csv_file, writer)

    def _write_results_summary(self, csv_file):
        self._write_mvs_count_summary(csv_file)
        self._write_domain_count_summary(csv_file)

    def write_results_to_csv(self, csv_filename):
        if self.mvs_results.get_device_map():
            with open(csv_filename, 'w') as csv_file:
                writer = csv.DictWriter(csv_file, self.LOG_SOURCE_COLUMN_ORDER)
                self._write_results_summary(csv_file)
                self.add_blank_row(csv_file)
                self._write_mvs_device_list(csv_file)
                self.add_blank_row(csv_file)
                self._write_log_source_details(csv_file, writer)

    def output_results(self):
        print('MVS count for the deployment is {}'.format(self.mvs_results.get_mvs_count()))
        if self.mvs_results.get_domain_count_map():
            domains = list(self.mvs_results.get_domain_count_map().keys())
            domains.sort()
            for domain in domains:
                print('MVS count for domain {} is {}'.format(domain, self.mvs_results.get_domain_count_map()[domain]))


class Validator(object):

    @staticmethod
    def is_console():
        try:
            is_c = MyVer.is_console()
            logging.debug('is_console output is %s', is_c)
            return is_c
        except (MyVerException) as err:
            logging.error('is_console failed with the following error %s', str(err))
        return False

    @staticmethod
    def perform_api_permission_check(aql_client):
        return aql_client.check_api_permissions()


class MyVer(object):

    @staticmethod
    def _query(arg):
        try:
            cmd_args = ['/opt/qradar/bin/myver', arg]
            cmd_result = subprocess.check_output(cmd_args)
            if cmd_result:
                cmd_output = cmd_result.rstrip()
                return cmd_output
            return ''
        except (subprocess.CalledProcessError) as err:
            raise MyVerException(err)

    @staticmethod
    def get_hostname():
        return MyVer._query('-vh')

    @staticmethod
    def is_console():
        return MyVer._query('-c') == 'true'


class MVSProcessor(object):

    DEFAULT_LOG_FILE = '/var/log/countMVS.log'
    DEFAULT_CSV_OUTPUT_FILE = 'mvsCount.csv'
    DEFAULT_QRADAR_DB_NAME = 'qradar'
    DEFAULT_QRADAR_DB_USER = 'qradar'
    DEFAULT_PERIOD_IN_DAYS = 1
    MAXIMUM_PERIOD_IN_DAYS = 10
    DAY_IN_MILLISECONDS = 86400000

    def __init__(self, db_service=None, aql_client=None):
        self.log_file = self.DEFAULT_LOG_FILE
        self.csv_file = self.DEFAULT_CSV_OUTPUT_FILE
        self.db_service = db_service
        self.aql_client = aql_client
        self.db_client = None
        self.multi_domain = False
        self.period_in_days = self.DEFAULT_PERIOD_IN_DAYS

    def _init_log_files(self, args):
        if args and 'o' in args and args['o']:
            self.csv_file = args['o']
        if args and 'l' in args and args['l']:
            self.log_file = args['l']

    def _init_logging(self, args):
        if args and 'debug' in args and args['debug']:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        logging.basicConfig(level=log_level,
                            format='%(asctime)s %(levelname)s %(message)s',
                            filename=self.log_file,
                            filemode='w')

    def _init_db_service(self):
        if not self.db_service:
            try:
                self.db_client = DatabaseClient(self.DEFAULT_QRADAR_DB_NAME, self.DEFAULT_QRADAR_DB_USER)
                logging.info('Attempting to connect to database %s with username %s', self.DEFAULT_QRADAR_DB_NAME,
                             self.DEFAULT_QRADAR_DB_USER)
                self.db_client.connect()
                logging.info('Connected to qradar database successfully')
                self.db_service = DatabaseService(self.db_client)
            except DatabaseError as err:
                logging.error('Unable to connect to database\n'\
                              'Reason[%s]', err)
                raise DatabaseError('Unable to connect to database')

    def _init_aql_client(self, insecure):
        if not self.aql_client:
            auth = AuthReader.prompt_for_auth_method()
            if not auth:
                raise QuitSelected()

            logging.debug('retrieving console hostname')
            hostname = MyVer.get_hostname()

            logging.debug('initializing aql client')
            api_client = RESTClient(hostname, insecure)
            api_client.set_client_auth(auth)
            self.aql_client = AQLClient(api_client)

    @staticmethod
    def _parse_arguments():
        parser = argparse.ArgumentParser()
        parser.add_argument('-d', '--debug', help='sets the log level to debug', action='store_true')
        parser.add_argument('-i',
                            '--insecure',
                            help='skips certificate verification for HTTP requests',
                            action='store_true')
        parser.add_argument('-o', metavar='<filename>', help='overrides the default output csv file')
        parser.add_argument('-l', metavar='<filename>', help='overrides the default file to log to')
        return vars(parser.parse_args())

    def _get_domain_appender(self):
        if self.multi_domain:
            return DomainAppender(multi_domain=True, aql_client=self.aql_client, period_in_days=self.period_in_days)
        return DomainAppender(multi_domain=False)

    def _append_domains(self, log_source_map):
        if log_source_map:
            domain_appender = self._get_domain_appender()
            domain_appender.add_domains(log_source_map)

    def _process_log_sources(self, log_sources):
        log_source_processor = LogSourceProcessor(self.db_service, self.aql_client, self.multi_domain)
        log_source_processor.process_log_sources(log_sources, self.period_in_days)
        return log_source_processor

    def _output_results(self, mvs_results):
        results_generator = ResultsGenerator(mvs_results, self.period_in_days)
        results_generator.write_results_to_csv(self.csv_file)
        results_generator.output_results()

    def _close_db_connection(self):
        if self.db_client:
            self.db_client.close()

    def _build_log_source_map(self):
        self._init_db_service()
        yesterday = int(round(time.time() * 1000)) - (int(self.period_in_days) * self.DAY_IN_MILLISECONDS)
        return self.db_service.build_log_source_map(yesterday)

    def _store_domain_setup(self):
        domain_count = self.db_service.get_domain_count()
        if domain_count > 1:
            self.multi_domain = True
        logging.info('Count of domains is %d', domain_count)
        logging.info('Multi-Domain system is %s', self.multi_domain)

    def _store_period_in_days(self):
        time_period_reader = TimePeriodReader()
        self.period_in_days = time_period_reader.prompt_for_time_period(self.DEFAULT_PERIOD_IN_DAYS,
                                                                        self.MAXIMUM_PERIOD_IN_DAYS)

    def _build_log_sources_list(self):
        log_source_map = self._build_log_source_map()
        self._store_domain_setup()
        self._append_domains(log_source_map)
        return log_source_map.values()

    def _generate_mvs_results(self, args):
        insecure = False
        if args and 'insecure' in args and args['insecure']:
            insecure = True
        self._store_period_in_days()
        self._init_aql_client(insecure)
        permission_check_result = Validator.perform_api_permission_check(self.aql_client)
        if not permission_check_result.is_successful():
            raise ValidatorException(permission_check_result.get_error_message())
        log_sources = self._build_log_sources_list()
        log_source_processor = self._process_log_sources(log_sources)
        mvs_results = log_source_processor.get_mvs_results()
        self._output_results(mvs_results)
        logging.info('Total log sources considered = %s', mvs_results.get_log_source_count())

    def run(self):
        try:
            args = self._parse_arguments()
            self._init_log_files(args)
            self._init_logging(args)
            if not Validator.is_console():
                raise ValidatorException('This script can only be ran on the console. Exiting...')
            self._generate_mvs_results(args)
            return 0
        except (DatabaseError, DomainRetrievalException, IOError, LogSourceRetrievalException, ValidatorException,
                WindowsWorkstationRetrievalException, MyVerException) as err:
            print(err)
            return 1
        except KeyboardInterrupt:
            print('\nExiting...')
            return 1
        except QuitSelected:
            return 0
        finally:
            self._close_db_connection()


if __name__ == '__main__':
    sys.exit(MVSProcessor().run())
