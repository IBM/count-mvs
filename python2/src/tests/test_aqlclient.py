#! /usr/bin/env python

from mock import Mock
from countMVS import Auth, APIError, APIErrorGenerator, AQLClient, \
DomainAppender, LogSourceToDomainMapping, RESTException
from tests.test_api_error_generator import DEFAULT_DETAILED_ERROR_MESSAGE, DEFAULT_ERROR_MESSAGE, FORBIDDEN_HTTP_CODE
from tests.utils import read_response_from_file

DEFAULT_ERROR_MESSAGE = 'error'
DEFAULT_DETAILED_ERROR_MESSAGE = 'error'
CREATED_HTTP_CODE = 201
FORBIDDEN_HTTP_CODE = 403
DUMMY_AUTH_TOKEN = '8aaca289-e345-449f-b629-9b2245ceee34'
SYSTEM_ABOUT_RESPONSE_JSON_FILE = 'system_about.json'
ARIEL_POST_RESPONSE_JSON_FILE = 'post_search.json'
ARIEL_RESULTS_RESPONSE_JSON_FILE = 'ariel_results.json'
ARIEL_SEARCH_ID = '84570b06-9c87-4f4a-990b-3bd7f0a94299'
DEFAULT_DOMAIN_NAME = 'Default Domain'
ARIEL_WAIT_STATUS = 'WAIT'
LOG_SOURCE_ID_ONE = 70
LOG_SOURCE_ID_TWO = 71
QUERY_EXPRESSION_HEADER = 'query_expression'


def build_api_error(response_code, error=DEFAULT_ERROR_MESSAGE, detailed_error=DEFAULT_DETAILED_ERROR_MESSAGE):
    api_error = APIError()
    api_error.set_response_code(response_code)
    api_error.set_error_message(error)
    api_error.set_detailed_error_message(detailed_error)
    return api_error


def build_client_auth(password=None, token=None):
    client_auth = Auth()
    if password:
        client_auth.set_password(password)
    if token:
        client_auth.set_auth_services_token(token)
    return client_auth


def build_mock_rest_client(client_auth=None, get_response_file=None, post_response_file=None, api_error=None):
    rest_client = Mock()
    if post_response_file:
        rest_client.post.return_value = read_response_from_file(post_response_file)
    if get_response_file:
        rest_client.get.return_value = read_response_from_file(get_response_file)
    if api_error:
        rest_client.get.side_effect = RESTException(api_error.get_error_message(), api_error)
    rest_client.get_client_auth.return_value = client_auth
    return rest_client


def build_log_source_to_domain_mapping(ariel_results):
    mapping = LogSourceToDomainMapping()
    for ariel_result in ariel_results:
        mapping.add_mapping_from_json(ariel_result)
    return mapping.get_logsource_to_domain()


def test_perform_search():
    rest_client = build_mock_rest_client(post_response_file=ARIEL_POST_RESPONSE_JSON_FILE)
    aql_client = AQLClient(rest_client)
    domain_aql_query = DomainAppender.DOMAIN_AQL_QUERY_TEMPLATE.format(1)
    ariel_search = aql_client.perform_search(domain_aql_query)
    expected_params = {QUERY_EXPRESSION_HEADER: domain_aql_query}
    rest_client.post.assert_called_with(url=AQLClient.ARIEL_SEARCHES_ENDPOINT,
                                        success_code=CREATED_HTTP_CODE,
                                        params=expected_params)
    assert ariel_search.get_search_id() == ARIEL_SEARCH_ID
    assert ariel_search.is_completed() is False
    assert ariel_search.get_progress() == 0
    assert ariel_search.get_status() == ARIEL_WAIT_STATUS


def test_get_search():
    rest_client = build_mock_rest_client(get_response_file=ARIEL_POST_RESPONSE_JSON_FILE)
    aql_client = AQLClient(rest_client)
    ariel_search = aql_client.get_search(ARIEL_SEARCH_ID)
    rest_client.get.assert_called_with(url=AQLClient.ARIEL_SEARCH_ENDPOINT.format(ARIEL_SEARCH_ID))
    assert ariel_search.get_search_id() == ARIEL_SEARCH_ID
    assert ariel_search.is_completed() is False
    assert ariel_search.get_progress() == 0
    assert ariel_search.get_status() == ARIEL_WAIT_STATUS


def test_get_search_results():
    rest_client = build_mock_rest_client(get_response_file=ARIEL_RESULTS_RESPONSE_JSON_FILE)
    aql_client = AQLClient(rest_client)
    ariel_results = aql_client.get_search_result(ARIEL_SEARCH_ID)
    rest_client.get.assert_called_with(headers=None,
                                       url=AQLClient.ARIEL_SEARCH_RESULTS_ENDPOINT.format(ARIEL_SEARCH_ID))
    assert len(ariel_results) == 2
    log_source_to_domain_map = build_log_source_to_domain_mapping(ariel_results)
    assert log_source_to_domain_map[LOG_SOURCE_ID_ONE][0] == DEFAULT_DOMAIN_NAME
    assert log_source_to_domain_map[LOG_SOURCE_ID_TWO][0] == DEFAULT_DOMAIN_NAME


def test_permissions_check_with_permissions():
    rest_client = build_mock_rest_client(build_client_auth(token=DUMMY_AUTH_TOKEN),
                                         get_response_file=SYSTEM_ABOUT_RESPONSE_JSON_FILE)
    aql_client = AQLClient(rest_client)
    permission_check = aql_client.check_api_permissions()
    assert permission_check.is_successful() is True
    assert permission_check.get_response_json() == read_response_from_file(SYSTEM_ABOUT_RESPONSE_JSON_FILE)


def test_permissions_check_with_no_permissions():
    rest_client = build_mock_rest_client(build_client_auth(token=DUMMY_AUTH_TOKEN),
                                         api_error=build_api_error(FORBIDDEN_HTTP_CODE,
                                                                   error=DEFAULT_ERROR_MESSAGE,
                                                                   detailed_error=DEFAULT_DETAILED_ERROR_MESSAGE))
    aql_client = AQLClient(rest_client)
    permission_check = aql_client.check_api_permissions()
    assert permission_check.is_successful() is False
    assert permission_check.get_error_message() == APIErrorGenerator.TOKEN_PERMISSIONS_ERROR
