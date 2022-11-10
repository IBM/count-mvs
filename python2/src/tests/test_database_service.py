#! /usr/bin/env python

from mock import Mock
import pytest
from psycopg2 import DatabaseError
from countMVS import DatabaseService, DomainRetrievalException, LogSource, LogSourceRetrievalException, TooManyResultsError
from tests.utils import read_db_row_from_file, read_db_rows_from_file

LOG_SOURCE_ROWS_HAPPY_PATH_JSON_FILE = 'log_source_rows_happy_path.json'
SINGLE_LOG_SOURCE_JSON_FILE = 'single_log_source.json'
SINGLE_LOG_SOURCE_NON_ZERO_SPCONFIG_JSON_FILE = 'single_log_source_non_zero_spconfig.json'
SENSOR_PROTOCOL_CONFIG_JSON_FILE = 'sensor_protocol_config.json'
SENSOR_PROTOCOL_CONFIG_PARAMETER_JSON_FILE = 'sensor_protocol_config_parameter.json'
QIDS_JSON_FILE = 'qids.json'
COUNT_COLUMN_NAME = 'count'
DATABASE_DUMMY_ERROR = 'test error'


def test_get_machine_identifier_no_sensor_protocol_id():
    row = read_db_row_from_file(SINGLE_LOG_SOURCE_JSON_FILE)
    log_source = LogSource.load_from_db_row(row)
    db_client = Mock()
    db_client.fetch_one.return_value = None
    db_service = DatabaseService(db_client)
    assert db_service.get_machine_identifier(log_source) == "1.1.1.1"


def test_get_machine_identifier_with_config_param_value():
    row = read_db_row_from_file(SINGLE_LOG_SOURCE_NON_ZERO_SPCONFIG_JSON_FILE)
    log_source = LogSource.load_from_db_row(row)
    db_client = Mock()
    sensor_protocol_config_json = read_db_row_from_file(SENSOR_PROTOCOL_CONFIG_JSON_FILE)
    sensor_protocol_config_parameter_json = read_db_row_from_file(SENSOR_PROTOCOL_CONFIG_PARAMETER_JSON_FILE)
    db_client.fetch_one.side_effect = [sensor_protocol_config_json, sensor_protocol_config_parameter_json]
    db_service = DatabaseService(db_client)
    assert db_service.get_machine_identifier(log_source) == "1.2.3.4"


def test_get_machine_identifier_with_no_config_param_value():
    row = read_db_row_from_file(SINGLE_LOG_SOURCE_NON_ZERO_SPCONFIG_JSON_FILE)
    log_source = LogSource.load_from_db_row(row)
    db_client = Mock()
    sensor_protocol_config_json = read_db_row_from_file(SENSOR_PROTOCOL_CONFIG_JSON_FILE)
    db_client.fetch_one.side_effect = [sensor_protocol_config_json, None]
    db_service = DatabaseService(db_client)
    assert db_service.get_machine_identifier(log_source) == "1.1.1.1"


def test_get_machine_identifier_exception_handled():
    row = read_db_row_from_file(SINGLE_LOG_SOURCE_NON_ZERO_SPCONFIG_JSON_FILE)
    log_source = LogSource.load_from_db_row(row)
    db_client = Mock()
    db_client.fetch_one.side_effect = TooManyResultsError(DATABASE_DUMMY_ERROR)
    db_service = DatabaseService(db_client)
    assert db_service.get_machine_identifier(log_source) == "1.1.1.1"


def test_build_log_source_map_happy_path():
    rows = read_db_rows_from_file(LOG_SOURCE_ROWS_HAPPY_PATH_JSON_FILE)
    db_client = Mock()
    db_client.fetch_all.return_value = rows
    db_service = DatabaseService(db_client)
    log_source_map = db_service.build_log_source_map(1)
    assert len(log_source_map.keys()) == 2


def test_build_log_source_map_database_error():
    db_client = Mock()
    db_client.fetch_all.side_effect = DatabaseError(DATABASE_DUMMY_ERROR)
    db_service = DatabaseService(db_client)
    with pytest.raises(LogSourceRetrievalException) as exception:
        db_service.build_log_source_map(1)
    assert 'Unable to retrieve log sources from the database, Reason [{}]'.format(DATABASE_DUMMY_ERROR) in str(
        exception)
    db_client.fetch_all.assert_called_with(DatabaseService.LOG_SOURCE_RETRIEVAL_QUERY.format(1))


def test_domain_count_happy_path():
    db_client = Mock()
    db_result = {}
    db_result[COUNT_COLUMN_NAME] = 2
    db_client.fetch_one.return_value = db_result
    db_service = DatabaseService(db_client)
    assert db_service.get_domain_count() == 2


def test_domain_count_empty_response():
    db_client = Mock()
    db_result = None
    db_client.fetch_one.return_value = db_result
    db_service = DatabaseService(db_client)
    with pytest.raises(DomainRetrievalException) as exception:
        db_service.get_domain_count()
    assert 'No result returned when executing query {}'.format(DatabaseService.DOMAIN_COUNT_QUERY) in str(exception)


def test_domain_count_too_many_results():
    db_client = Mock()
    db_client.fetch_one.side_effect = TooManyResultsError(DATABASE_DUMMY_ERROR)
    db_service = DatabaseService(db_client)
    with pytest.raises(DomainRetrievalException) as exception:
        db_service.get_domain_count()
    assert 'Unable to retrieve domain count from the database, {}'.format(DATABASE_DUMMY_ERROR) in str(exception)


def test_domain_count_exception():
    db_client = Mock()
    db_client.fetch_one.side_effect = DatabaseError(DATABASE_DUMMY_ERROR)
    db_service = DatabaseService(db_client)
    with pytest.raises(DomainRetrievalException) as exception:
        db_service.get_domain_count()
    assert 'Unable to retrieve domain count from the database, {}'.format(DATABASE_DUMMY_ERROR) in str(exception)


def test_get_windows_server_qids():
    qids = read_db_row_from_file(QIDS_JSON_FILE)
    db_client = Mock()
    db_client.fetch_all.return_value = qids
    db_service = DatabaseService(db_client)
    assert all(elem in db_service.get_windows_server_qids() for elem in [5000921, 5000569, 5002963, 5000899])
