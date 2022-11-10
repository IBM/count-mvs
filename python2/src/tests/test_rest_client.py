#! /usr/bin/env python

import pytest
from requests.exceptions import RequestException
from mock import Mock, patch
from countMVS import APIException, ArielSearch, AQLClient, Auth, DomainAppender, RESTClient, RESTException
from tests.utils import read_response_from_file


def test_rest_client_get_with_password():
    rest_client = RESTClient()
    client_auth = Auth()
    client_auth.set_password('test')
    rest_client.set_client_auth(client_auth)
    with patch("requests.get") as mock_requests_get:
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = read_response_from_file('post_search.json')
        mock_requests_get.return_value = response_mock
        response_json = rest_client.get(
            url=AQLClient.ARIEL_SEARCH_ENDPOINT.format('84570b06-9c87-4f4a-990b-3bd7f0a94299'))
        ariel_search = ArielSearch.from_json(response_json)
        assert ariel_search.get_search_id() == '84570b06-9c87-4f4a-990b-3bd7f0a94299'
        assert ariel_search.is_completed() is False
        assert ariel_search.get_progress() == 0
        assert ariel_search.get_status() == 'WAIT'
        mock_requests_get.assert_called_with(
            AQLClient.ARIEL_SEARCH_ENDPOINT.format('84570b06-9c87-4f4a-990b-3bd7f0a94299'),
            headers={},
            auth=('admin', 'test'),
            verify=False)


def test_rest_client_get_with_auth_token():
    rest_client = RESTClient()
    client_auth = Auth()
    client_auth.set_auth_services_token('test')
    rest_client.set_client_auth(client_auth)
    with patch("requests.get") as mock_requests_get:
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = read_response_from_file('post_search.json')
        mock_requests_get.return_value = response_mock
        response_json = rest_client.get(
            url=AQLClient.ARIEL_SEARCH_ENDPOINT.format('84570b06-9c87-4f4a-990b-3bd7f0a94299'))
        ariel_search = ArielSearch.from_json(response_json)
        assert ariel_search.get_search_id() == '84570b06-9c87-4f4a-990b-3bd7f0a94299'
        assert ariel_search.is_completed() is False
        assert ariel_search.get_progress() == 0
        assert ariel_search.get_status() == 'WAIT'
        mock_requests_get.assert_called_with(
            AQLClient.ARIEL_SEARCH_ENDPOINT.format('84570b06-9c87-4f4a-990b-3bd7f0a94299'),
            headers={'SEC': 'test'},
            auth=None,
            verify=False)


def test_rest_client_post_with_password():
    rest_client = RESTClient()
    client_auth = Auth()
    client_auth.set_password('test')
    rest_client.set_client_auth(client_auth)
    with patch("requests.post") as mock_requests_post:
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = read_response_from_file('post_search.json')
        mock_requests_post.return_value = response_mock
        domain_aql_query = DomainAppender.DOMAIN_AQL_QUERY_TEMPLATE.format(1)
        query_params = {'query_expression', domain_aql_query}
        response_json = rest_client.post(url=AQLClient.ARIEL_SEARCHES_ENDPOINT, params=query_params)
        ariel_search = ArielSearch.from_json(response_json)
        assert ariel_search.get_search_id() == '84570b06-9c87-4f4a-990b-3bd7f0a94299'
        assert ariel_search.is_completed() is False
        assert ariel_search.get_progress() == 0
        assert ariel_search.get_status() == 'WAIT'
        mock_requests_post.assert_called_with(AQLClient.ARIEL_SEARCHES_ENDPOINT,
                                              headers={},
                                              params=query_params,
                                              auth=('admin', 'test'),
                                              verify=False)


def test_rest_client_post_non_success_response_code():
    rest_client = RESTClient()
    client_auth = Auth()
    client_auth.set_password('test')
    rest_client.set_client_auth(client_auth)
    with patch("requests.post") as mock_requests_post:
        response_mock = Mock()
        response_mock.status_code = 401
        response_mock.json.return_value = read_response_from_file('unauthorized.json')
        mock_requests_post.return_value = response_mock
        domain_aql_query = DomainAppender.DOMAIN_AQL_QUERY_TEMPLATE.format(1)
        query_params = {'query_expression', domain_aql_query}
        with pytest.raises(RESTException) as exception:
            rest_client.post(url=AQLClient.ARIEL_SEARCHES_ENDPOINT, params=query_params)
        assert 'You are unauthorized to access the requested resource.' in str(exception)


def test_rest_client_get_non_success_response_code():
    rest_client = RESTClient()
    client_auth = Auth()
    client_auth.set_password('test')
    rest_client.set_client_auth(client_auth)
    with patch("requests.get") as mock_requests_get:
        response_mock = Mock()
        response_mock.status_code = 401
        response_mock.json.return_value = read_response_from_file('unauthorized.json')
        mock_requests_get.return_value = response_mock
        with pytest.raises(RESTException) as exception:
            rest_client.get(url=AQLClient.ARIEL_SEARCH_ENDPOINT.format('84570b06-9c87-4f4a-990b-3bd7f0a94299'))
        assert 'You are unauthorized to access the requested resource.' in str(exception)


def test_rest_client_get_request_error():
    rest_client = RESTClient()
    client_auth = Auth()
    client_auth.set_password('test')
    rest_client.set_client_auth(client_auth)
    with patch("requests.get") as mock_requests_get:
        mock_requests_get.side_effect = RequestException('error')
        with pytest.raises(APIException) as exception:
            rest_client.get(url=AQLClient.ARIEL_SEARCH_ENDPOINT.format('84570b06-9c87-4f4a-990b-3bd7f0a94299'))
        assert 'error' in str(exception)


def test_rest_client_post_request_error():
    rest_client = RESTClient()
    client_auth = Auth()
    client_auth.set_password('test')
    rest_client.set_client_auth(client_auth)
    with patch("requests.post") as mock_requests_post:
        mock_requests_post.side_effect = ValueError('error')
        domain_aql_query = DomainAppender.DOMAIN_AQL_QUERY_TEMPLATE.format(1)
        query_params = {'query_expression', domain_aql_query}
        with pytest.raises(APIException) as exception:
            rest_client.post(url=AQLClient.ARIEL_SEARCHES_ENDPOINT, params=query_params)
        assert 'error' in str(exception)
