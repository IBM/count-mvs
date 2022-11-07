#! /usr/bin/env python

from mock import Mock
import pytest
from countMVS import APIException, ArielSearch, DomainAppender, DomainRetrievalException, LogSource, RESTException


def build_mock_event(log_source_id, domain_name):
    event = {}
    event['logsourceid'] = log_source_id
    event['domainname_domainid'] = domain_name
    return event


def build_mock_events(multiple_domains=False):
    events = []
    for domain_id in range(1, 5):
        if multiple_domains:
            domain_name_one = 'Test Domain {}a'.format(domain_id)
            domain_name_two = 'Test Domain {}b'.format(domain_id)
            event_one = build_mock_event(domain_id, domain_name_one)
            event_two = build_mock_event(domain_id, domain_name_two)
            events.append(event_one)
            events.append(event_two)
        else:
            domain_name = 'Test Domain {}'.format(domain_id)
            event = build_mock_event(domain_id, domain_name)
            events.append(event)
    return events


def build_mock_log_source_map():
    log_source_map = {}
    for log_source_id in range(1, 5):
        log_source = LogSource()
        log_source_map[log_source_id] = log_source
    return log_source_map


def build_mock_aql_client(multiple_domains=False, search_status='COMPLETED', raised_exception=None):
    events = build_mock_events(multiple_domains)
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


def test_default_domain_added_with_no_domains():
    log_source_map = build_mock_log_source_map()
    appender = DomainAppender(False)
    appender.add_domains(log_source_map)
    for log_source_id in log_source_map:
        log_source = log_source_map[log_source_id]
        domains = log_source.get_domains()
        assert len(domains) == 1
        assert log_source.get_first_domain() == 'Default Domain'


def test_adding_single_domain():
    aql_client = build_mock_aql_client()
    log_source_map = build_mock_log_source_map()
    appender = DomainAppender(True, aql_client)
    appender.add_domains(log_source_map)
    for log_source_id in log_source_map:
        log_source = log_source_map[log_source_id]
        domains = log_source.get_domains()
        assert len(domains) == 1
        assert log_source.get_first_domain() == 'Test Domain {}'.format(log_source_id)


def test_adding_multiple_domains():
    aql_client = build_mock_aql_client(True)
    log_source_map = build_mock_log_source_map()
    appender = DomainAppender(True, aql_client)
    appender.add_domains(log_source_map)
    for log_source_id in log_source_map:
        log_source = log_source_map[log_source_id]
        domains = log_source.get_domains()
        assert len(domains) == 2
        assert domains[0] == 'Test Domain {}a'.format(log_source_id)
        assert domains[1] == 'Test Domain {}b'.format(log_source_id)


def test_exception_thrown_when_ariel_search_fails():
    aql_client = build_mock_aql_client(True, 'ERROR')
    log_source_map = build_mock_log_source_map()
    appender = DomainAppender(True, aql_client)
    with pytest.raises(DomainRetrievalException) as exception:
        appender.add_domains(log_source_map)
    assert 'Ariel search did not complete successfully, status is ERROR' in str(exception)


def test_exception_thrown_when_ariel_search_cancelled():
    aql_client = build_mock_aql_client(True, 'CANCELED')
    log_source_map = build_mock_log_source_map()
    appender = DomainAppender(True, aql_client)
    with pytest.raises(DomainRetrievalException) as exception:
        appender.add_domains(log_source_map)
    assert 'Ariel search did not complete successfully, status is CANCELED' in str(exception)


def test_client_api_exception_throws_exception():
    exception = APIException('API Exception')
    aql_client = build_mock_aql_client(True, 'COMPLETED', exception)
    log_source_map = build_mock_log_source_map()
    appender = DomainAppender(True, aql_client)
    with pytest.raises(DomainRetrievalException) as exception:
        appender.add_domains(log_source_map)
        assert 'API Exception' in str(exception)


def test_client_rest_exception_throws_exception():
    exception = RESTException('REST Exception')
    aql_client = build_mock_aql_client(True, 'COMPLETED', exception)
    log_source_map = build_mock_log_source_map()
    appender = DomainAppender(True, aql_client)
    with pytest.raises(DomainRetrievalException) as exception:
        appender.add_domains(log_source_map)
        assert 'REST Exception' in str(exception)
