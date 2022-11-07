#! /usr/bin/env python

from mock import Mock, mock_open, patch
from countMVS import ArielSearch, LogSource, MVSResults, WindowsDeviceProcessor
from tests.utils import read_db_row_from_file, read_db_rows_from_file, read_response_from_file

QIDS_JSON_FILE = 'qids.json'
PERFORM_WINDOWS_SEARCH_JSON_FILE = 'perform_windows_search.json'
WINDOWS_SEARCH_JSON_FILE = 'windows_search.json'
WINDOWS_SERVER_LOG_SOURCE_JSON_FILE = 'windows_server_log_source.json'
WINDOWS_WORKSTATION_LOG_SOURCE_JSON_FILE = 'windows_workstation_log_source.json'


def build_mock_aql_client():
    perform_windows_search_json = read_response_from_file(PERFORM_WINDOWS_SEARCH_JSON_FILE)
    windows_search_json = read_response_from_file(WINDOWS_SEARCH_JSON_FILE)
    aql_client = Mock()
    perform_ariel_search = ArielSearch.from_json(perform_windows_search_json)
    ariel_search = ArielSearch.from_json(windows_search_json)
    aql_client.perform_search.return_value = perform_ariel_search
    aql_client.get_search.return_value = ariel_search
    aql_client.get_search_result.return_value = []
    return aql_client


def build_mock_db_service():
    qids = read_db_rows_from_file(QIDS_JSON_FILE)
    db_service = Mock()
    db_service.get_windows_server_qids.return_value = qids
    return db_service


def build_mock_mvs_results(add_server_log_source=False):
    mvs_results = MVSResults()
    device_map = {}
    windows_log_source_row = read_db_row_from_file(WINDOWS_WORKSTATION_LOG_SOURCE_JSON_FILE)
    log_sources = []
    log_source = LogSource.load_from_db_row(windows_log_source_row)
    log_sources.append(log_source)
    if add_server_log_source:
        windows_server_log_source_row = read_db_row_from_file(WINDOWS_SERVER_LOG_SOURCE_JSON_FILE)
        server_log_source = LogSource.load_from_db_row(windows_server_log_source_row)
        log_sources.append(server_log_source)
    device_map['127.0.0.1'] = log_sources
    mvs_results.set_device_map(device_map)
    return mvs_results


def test_windows_workstation():
    aql_client = build_mock_aql_client()
    db_service = build_mock_db_service()
    mvs_results = build_mock_mvs_results()
    mocked_open_function = mock_open()
    with patch("builtins.open", mocked_open_function):
        processor = WindowsDeviceProcessor(aql_client, db_service, mvs_results)
        processor.process_devices()
        windows_workstations = processor.get_windows_workstations()
        assert len(windows_workstations) == 1 and windows_workstations[0] == '127.0.0.1'


def test_cache_file_used():
    mocked_open_function = mock_open(read_data="127.0.0.1")
    aql_client = build_mock_aql_client()
    db_service = build_mock_db_service()
    mvs_results = build_mock_mvs_results()
    with patch("os.path") as mock_os_path, patch("builtins.open", mocked_open_function) as mock_with_open:
        mock_os_path.exists.return_value = True
        processor = WindowsDeviceProcessor(aql_client, db_service, mvs_results)
        processor.process_devices()
        windows_workstations = processor.get_windows_workstations()
        assert len(windows_workstations) == 1 and windows_workstations[0] == '127.0.0.1'


def test_windows_server_excluded():
    aql_client = build_mock_aql_client()
    db_service = build_mock_db_service()
    mvs_results = build_mock_mvs_results(add_server_log_source=True)
    mocked_open_function = mock_open()
    with patch("builtins.open", mocked_open_function):
        processor = WindowsDeviceProcessor(aql_client, db_service, mvs_results)
        processor.process_devices()
        windows_workstations = processor.get_windows_workstations()
        assert len(windows_workstations) == 0
