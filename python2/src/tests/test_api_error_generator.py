#! /usr/bin/env python
from countMVS import APIError, APIErrorGenerator, APIException, Auth, RESTException

DEFAULT_ERROR_MESSAGE = 'error'
DEFAULT_DETAILED_ERROR_MESSAGE = 'error'
LOCKED_OUT_ERROR_MESSAGE = 'locked out'
DUMMY_PASSWORD = 'test'
DUMMY_AUTH_TOKEN = '8aaca289-e345-449f-b629-9b2245ceee34'
UNAUTHORIZED_HTTP_CODE = 401
FORBIDDEN_HTTP_CODE = 403
INTERNAL_SERVER_ERROR_CODE = 500


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


def build_rest_exception(api_error):
    return RESTException(api_error.get_error_message, api_error)


def build_api_exception(error):
    return APIException(error)


def test_incorrect_password_message():
    error_generator = APIErrorGenerator(build_client_auth(password=DUMMY_PASSWORD),
                                        build_rest_exception(build_api_error(UNAUTHORIZED_HTTP_CODE)))
    assert error_generator.generate_error_message() == APIErrorGenerator.PASSWORD_AUTH_ERROR


def test_user_lockout_message():
    error_generator = APIErrorGenerator(
        build_client_auth(password=DUMMY_PASSWORD),
        build_rest_exception(build_api_error(401, detailed_error=LOCKED_OUT_ERROR_MESSAGE)))
    assert error_generator.generate_error_message() == APIErrorGenerator.LOCKED_OUT_ERROR


def test_incorrect_auth_token_message():
    error_generator = APIErrorGenerator(build_client_auth(token=DUMMY_AUTH_TOKEN),
                                        build_rest_exception(build_api_error(UNAUTHORIZED_HTTP_CODE)))
    assert error_generator.generate_error_message() == APIErrorGenerator.TOKEN_AUTH_ERROR


def test_incorrect_auth_token_permissions():
    error_generator = APIErrorGenerator(build_client_auth(token=DUMMY_AUTH_TOKEN),
                                        build_rest_exception(build_api_error(FORBIDDEN_HTTP_CODE)))
    assert error_generator.generate_error_message() == APIErrorGenerator.TOKEN_PERMISSIONS_ERROR


def test_generate_non_auth_rest_error():
    error_generator = APIErrorGenerator(build_client_auth(token=DUMMY_AUTH_TOKEN),
                                        build_rest_exception(build_api_error(INTERNAL_SERVER_ERROR_CODE)))
    assert error_generator.generate_error_message() == DEFAULT_DETAILED_ERROR_MESSAGE


def test_generate_api_request_error():
    error_generator = APIErrorGenerator(None, build_api_exception(DEFAULT_ERROR_MESSAGE))
    assert error_generator.generate_error_message() == DEFAULT_DETAILED_ERROR_MESSAGE
