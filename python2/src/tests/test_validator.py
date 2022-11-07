#! /usr/bin/env python

from mock import Mock, patch
from countMVS import Validator


def test_console_check_on_console():
    with patch('subprocess.check_output') as mock_check_output:
        #test with a space at the end of true
        mock_check_output.return_value = 'true '
        console_check_result = Validator.is_console()
        assert console_check_result is True
        #test with normal result of true from myver
        mock_check_output.return_value = 'true'
        console_check_result = Validator.is_console()
        assert console_check_result is True


def test_console_check_on_mhost():
    with patch('subprocess.check_output') as mock_subprocess:
        mock_subprocess.return_value = 'false'
        console_check_result = Validator.is_console()
        assert console_check_result is False


def test_permission_check():
    mock_aql_client = Mock()
    Validator.perform_api_permission_check(mock_aql_client)
    assert mock_aql_client.check_api_permissions.called
