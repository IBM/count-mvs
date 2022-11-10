#! /usr/bin/env python

from mock import Mock, patch
from countMVS import APIException, ArielSearch, LogSourceProcessor, LogSource, WindowsDeviceProcessor


def build_mock_aql_client(search_status='COMPLETED', raised_exception=None):
    events = []
    aql_client = Mock()
    ariel_search = ArielSearch()
    ariel_search.set_status(search_status)
    ariel_search.set_progress(100)
    ariel_search.set_completed(True)
    if raised_exception:
        aql_client.perform_search.side_effect = APIException('Test')
    else:
        aql_client.perform_search.return_value = ariel_search
    aql_client.get_search.return_value = ariel_search
    aql_client.get_search_result.return_value = events
    return aql_client


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


def build_excluded_log_sources_list():
    log_sources = []
    log_sources.append(build_log_source(1, 331, '1.1.1.1'))
    log_sources.append(build_log_source(2, 70, '2.2.2.2'))
    return log_sources


def build_empty_domain_log_source_list():
    log_sources = []
    log_sources.append(build_log_source(1, 71, '1.1.1.1', False))
    log_sources.append(build_log_source(2, 70, '2.2.2.2', False))
    return log_sources


def build_single_domain_log_source_list():
    log_sources = []
    log_sources.append(build_log_source(1, 71, '1.1.1.1', True))
    log_sources.append(build_log_source(2, 70, '2.2.2.2', True))
    return log_sources


def build_multi_domain_log_source_list():
    domains_one = ['Test Domain One', 'Test Domain Two']
    domains_two = ['Test Domain Three', 'Test Domain Four']
    log_sources = []
    log_sources.append(build_log_source(1, 71, '1.1.1.1', False, domains_one))
    log_sources.append(build_log_source(2, 70, '2.2.2.2', False, domains_two))
    return log_sources


def build_multi_domain_log_source_list_two():
    domains_one = ['Test Domain One', 'Test Domain Two']
    domains_two = ['Test Domain Three', 'Test Domain Four']
    log_sources = []
    log_sources.append(build_log_source(1, 71, '127.0.0.1', False, domains_one))
    log_sources.append(build_log_source(2, 70, '2.2.2.2', False, domains_two))
    return log_sources


def build_multi_domain_log_sources_with_duplicate_ips():
    domains_one = ['Test Domain One', 'Test Domain Two']
    domains_two = ['Test Domain Three', 'Test Domain Four']
    log_sources = []
    log_sources.append(build_log_source(1, 71, '127.0.0.1', False, domains_one))
    log_sources.append(build_log_source(2, 72, '127.0.0.1', False, domains_two))
    log_sources.append(build_log_source(3, 73, '2.2.2.2', False, domains_one))
    log_sources.append(build_log_source(4, 74, '2.2.2.2', False, domains_two))
    return log_sources


def build_log_sources_with_hostnames():
    domains_one = ['Test Domain One', 'Test Domain Two']
    log_sources = []
    log_sources.append(build_log_source(1, 71, 'microsoft.test.com', False, domains_one))
    return log_sources


def build_multi_domain_log_sources_with_duplicate_hostnames():
    domains_one = ['Test Domain One', 'Test Domain Two']
    domains_two = ['Test Domain Three', 'Test Domain Four']
    log_sources = []
    log_sources.append(build_log_source(1, 71, 'microsoft.test.com', False, domains_one))
    log_sources.append(build_log_source(2, 72, 'microsoft.test.net', False, domains_two))
    log_sources.append(build_log_source(3, 73, 'microsoft.sql.net', False, domains_one))
    log_sources.append(build_log_source(4, 74, 'microsoft.sql.net', False, domains_two))
    return log_sources


def build_multi_domain_log_sources_with_duplicate_hostnames_two():
    domains_one = ['Test Domain One', 'Test Domain Two']
    domains_two = ['Test Domain Three', 'Test Domain Four']
    log_sources = []
    log_sources.append(build_log_source(1, 71, '1.1.1.1', False, domains_one))
    log_sources.append(build_log_source(2, 72, 'microsoft.test.net', False, domains_two))
    log_sources.append(build_log_source(3, 73, '2.2.2.2', False, domains_one))
    log_sources.append(build_log_source(4, 74, 'microsoft.sql.net', False, domains_two))
    return log_sources


def hostname_machine_identifier(log_source):
    return log_source.get_hostname()


def build_mock_db_service():
    db_service = Mock()
    db_service.get_machine_identifier.side_effect = hostname_machine_identifier
    return db_service


def test_excluded_log_sources():
    db_service = build_mock_db_service()
    aql_client = build_mock_aql_client()
    processor = LogSourceProcessor(db_service, aql_client)
    log_sources = build_excluded_log_sources_list()
    processor.process_log_sources(log_sources)
    mvs_results = processor.get_mvs_results()
    assert len(mvs_results.get_device_map()) == 1
    assert (mvs_results.get_device_map().keys())[0] == '2.2.2.2'
    assert mvs_results.get_mvs_count() == 1
    assert not mvs_results.get_domain_count_map()


def test_empty_domain_log_sources_skipped():
    db_service = build_mock_db_service()
    aql_client = build_mock_aql_client()
    processor = LogSourceProcessor(db_service, aql_client)
    log_sources = build_empty_domain_log_source_list()
    processor.process_log_sources(log_sources)
    mvs_results = processor.get_mvs_results()
    assert not mvs_results.get_device_map()


def test_multiple_domains():
    db_service = build_mock_db_service()
    aql_client = build_mock_aql_client()
    processor = LogSourceProcessor(db_service, aql_client, True)
    log_sources = build_multi_domain_log_source_list()
    processor.process_log_sources(log_sources)
    mvs_results = processor.get_mvs_results()
    assert mvs_results.get_mvs_count() == 4
    assert len(mvs_results.get_device_map()) == 2
    assert len(mvs_results.get_domain_count_map()) == 4
    assert '1.1.1.1' in mvs_results.get_device_map().keys()
    assert '2.2.2.2' in mvs_results.get_device_map().keys()
    assert 'Test Domain One' in mvs_results.get_domain_count_map().keys()
    assert 'Test Domain Two' in mvs_results.get_domain_count_map().keys()
    assert 'Test Domain Three' in mvs_results.get_domain_count_map().keys()
    assert 'Test Domain Four' in mvs_results.get_domain_count_map().keys()
    assert mvs_results.get_domain_count_map()['Test Domain One'] == 1
    assert mvs_results.get_domain_count_map()['Test Domain Two'] == 1
    assert mvs_results.get_domain_count_map()['Test Domain Three'] == 1
    assert mvs_results.get_domain_count_map()['Test Domain Four'] == 1
    assert len(mvs_results.get_device_map()['1.1.1.1'][0].get_domains()) == 2
    assert len(mvs_results.get_device_map()['2.2.2.2'][0].get_domains()) == 2


def test_windows_workstations_removed():
    windows_workstations = []
    windows_workstations.append('127.0.0.1')
    with patch('countMVS.WindowsDeviceProcessor.get_windows_workstations', return_value=windows_workstations):
        db_service = build_mock_db_service()
        aql_client = build_mock_aql_client()
        processor = LogSourceProcessor(db_service, aql_client, True)
        log_sources = build_multi_domain_log_source_list_two()
        processor.process_log_sources(log_sources)
        mvs_results = processor.get_mvs_results()
        assert mvs_results.get_mvs_count() == 2
        assert '127.0.0.1' not in mvs_results.device_map.keys()


def test_single_domain_log_source_multi_domain():
    db_service = build_mock_db_service()
    aql_client = build_mock_aql_client()
    processor = LogSourceProcessor(db_service, aql_client, True)
    log_sources = build_single_domain_log_source_list()
    processor.process_log_sources(log_sources)
    mvs_results = processor.get_mvs_results()
    assert mvs_results.get_mvs_count() == 2


def test_multi_domain_same_ips():
    db_service = build_mock_db_service()
    aql_client = build_mock_aql_client()
    processor = LogSourceProcessor(db_service, aql_client, True)
    log_sources = build_multi_domain_log_sources_with_duplicate_ips()
    processor.process_log_sources(log_sources)
    mvs_results = processor.get_mvs_results()
    assert mvs_results.get_mvs_count() == 8


def test_hostname_to_ip_resolution():
    with patch('countMVS.IPParser.get_device_ip', return_value='1.1.1.1'):
        db_service = build_mock_db_service()
        aql_client = build_mock_aql_client()
        processor = LogSourceProcessor(db_service, aql_client, True)
        log_sources = build_log_sources_with_hostnames()
        processor.process_log_sources(log_sources)
        mvs_results = processor.get_mvs_results()
        assert mvs_results.get_mvs_count() == 2


def test_hostname_to_ip_resolution_with_no_ip():
    with patch('countMVS.IPParser.get_device_ip', return_value=None):
        db_service = build_mock_db_service()
        aql_client = build_mock_aql_client()
        processor = LogSourceProcessor(db_service, aql_client, True)
        log_sources = build_log_sources_with_hostnames()
        processor.process_log_sources(log_sources)
        mvs_results = processor.get_mvs_results()
        assert mvs_results.get_mvs_count() == 2
        assert len(mvs_results.get_device_map().keys()) == 1
        assert mvs_results.get_device_map().keys()[0] == 'microsoft.test.com'


def get_device_ip(hostname):
    if hostname == 'microsoft.test.net' or hostname == 'microsoft.test.com':
        return '1.1.1.1'
    return '2.2.2.2'


def test_hostname_to_ip_resolution_with_multiple_ips():
    with patch('countMVS.IPParser.get_device_ip', side_effect=get_device_ip):
        db_service = build_mock_db_service()
        aql_client = build_mock_aql_client()
        processor = LogSourceProcessor(db_service, aql_client, True)
        log_sources = build_multi_domain_log_sources_with_duplicate_hostnames()
        processor.process_log_sources(log_sources)
        mvs_results = processor.get_mvs_results()
        assert mvs_results.get_mvs_count() == 8


def test_hostname_to_ip_resolution_with_ips_and_hostnames():
    with patch('countMVS.IPParser.get_device_ip', side_effect=get_device_ip):
        db_service = build_mock_db_service()
        aql_client = build_mock_aql_client()
        processor = LogSourceProcessor(db_service, aql_client, True)
        log_sources = build_multi_domain_log_sources_with_duplicate_hostnames_two()
        processor.process_log_sources(log_sources)
        mvs_results = processor.get_mvs_results()
        assert mvs_results.get_mvs_count() == 4
