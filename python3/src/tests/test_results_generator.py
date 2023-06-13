#! /usr/bin/env python

import csv
import io
from mock import mock_open, patch
from countMVS import LogSource, MVSResults, ResultsGenerator
from tests.utils import read_db_row_from_file

ZSCALAR_LOG_SOURCE_JSON_FILE = 'zscalar_log_source.json'
WINDOWS_WORKSTATION_LOG_SOURCE_JSON_FILE = 'windows_workstation_log_source.json'
NO_DOMAIN_LOG_SOURCE_JSON_FILE = 'single_log_source.json'


def build_log_source(sensor_id, type_id, hostname=None, add_default_domain=True, domains=None):
    log_source = LogSource()
    log_source.set_sensor_device_id(sensor_id)
    log_source.set_device_type_id(type_id)
    if add_default_domain:
        log_source.add_domain('Default Domain')
    if domains:
        log_source.set_domains(domains)
    log_source.set_hostname(hostname)
    return log_source


def build_mock_device_map():
    domains_one = ['Test Domain One', 'Test Domain Two']
    domains_two = ['Test Domain Three', 'Test Domain Four']
    log_source_one = build_log_source(1, 71, '1.1.1.1', False, domains_one)
    log_source_two = build_log_source(2, 70, '2.2.2.2', False, domains_two)
    device_map = {}
    device_map['1.1.1.1'] = []
    device_map['1.1.1.1'].append(log_source_one)
    device_map['2.2.2.2'] = []
    device_map['2.2.2.2'].append(log_source_two)
    return device_map


def build_mock_excluded_log_source():
    zscalar_log_source_row = read_db_row_from_file(ZSCALAR_LOG_SOURCE_JSON_FILE)
    excluded_log_source = LogSource.load_from_db_row(zscalar_log_source_row)
    excluded_log_source.add_domain('Default Domain')
    return excluded_log_source


def build_mock_windows_workstation_log_sources():
    workstation_log_sources = []
    windows_workstation_log_source_row = read_db_row_from_file(WINDOWS_WORKSTATION_LOG_SOURCE_JSON_FILE)
    workstation_log_source = LogSource.load_from_db_row(windows_workstation_log_source_row)
    workstation_log_source.add_domain('Default Domain')
    workstation_log_sources.append(workstation_log_source)
    return workstation_log_sources


def build_mock_skipped_log_source():
    skipped_log_source_row = read_db_row_from_file(NO_DOMAIN_LOG_SOURCE_JSON_FILE)
    skipped_log_source = LogSource.load_from_db_row(skipped_log_source_row)
    return skipped_log_source


def build_mock_domain_count_map():
    domain_count_map = {}
    domain_count_map['Domain One'] = 2
    domain_count_map['Domain Two'] = 3
    return domain_count_map


def test_write_results_to_csv():
    output = io.StringIO()
    string_csv_writer = csv.writer(output)
    mocked_open_function = mock_open()
    mvs_results = MVSResults()
    mvs_results.set_domain_count_map(build_mock_domain_count_map())
    mvs_results.add_excluded_log_source(build_mock_excluded_log_source())
    mvs_results.add_skipped_log_source(build_mock_skipped_log_source())
    mvs_results.add_windows_workstation('127.0.0.1', build_mock_windows_workstation_log_sources())
    mvs_results.set_device_map(build_mock_device_map())
    with patch("csv.writer") as mock_csv_writer, patch("builtins.open", mocked_open_function) as mock_with_open:
        mock_csv_writer.return_value = string_csv_writer
        results_generator = ResultsGenerator(mvs_results, 1, False)
        results_generator.write_results_to_csv('test.csv')
        mock_with_open.assert_called_with('test.csv', 'w', encoding='utf8')
        print((output.getvalue()))


def test_output_results():
    mvs_results = MVSResults()
    mvs_results.set_mvs_count(5)
    mvs_results.set_domain_count_map(build_mock_domain_count_map())
    results_generator = ResultsGenerator(mvs_results, 1, False)
    results_generator.output_results()
