#! /usr/bin/env python

from mock import patch
from countMVS import AuthReader

INVALID_CHOICE = 'a'
QUIT_CHOICE = 'q'
PASSWORD_CHOICE = '1'
TOKEN_CHOICE = '2'
DUMMY_PASSWORD = 'test'
DUMMY_TOKEN = '75a8bbcd-4ae3-4418-b7b3-efab40a931f2'
ADMIN_USERNAME = 'admin'


def test_none_returned_when_quit_selected():
    with patch('six.moves.input') as mock_input:
        mock_input.return_value = QUIT_CHOICE
        client_auth = AuthReader.prompt_for_auth_method()
        mock_input.assert_called_with('Please enter your choice: ')
        assert client_auth is None


def test_password_selection():
    with patch('six.moves.input') as mock_input, patch('getpass.getpass') as mock_get_pass:
        mock_input.return_value = PASSWORD_CHOICE
        mock_get_pass.return_value = DUMMY_PASSWORD
        client_auth = AuthReader.prompt_for_auth_method()
        mock_input.assert_called_with('Please enter your choice: ')
        mock_get_pass.assert_called_with('Please input the admin user password: ')
        assert client_auth.get_password() == DUMMY_PASSWORD
        assert client_auth.get_username() == ADMIN_USERNAME
        assert client_auth.password_authentication() is True
        assert client_auth.token_authentication() is False


def test_auth_token_selection():
    with patch('six.moves.input') as mock_input, patch('getpass.getpass') as mock_get_pass:
        mock_input.return_value = TOKEN_CHOICE
        mock_get_pass.return_value = DUMMY_TOKEN
        client_auth = AuthReader.prompt_for_auth_method()
        mock_input.assert_called_with('Please enter your choice: ')
        mock_get_pass.assert_called_with('Please input the security token for your authorized service: ')
        assert client_auth.get_auth_services_token() == DUMMY_TOKEN
        assert client_auth.token_authentication() is True
        assert client_auth.password_authentication() is False


def test_invalid_option(capsys):
    with patch('six.moves.input') as mock_input:
        mock_input.side_effect = [INVALID_CHOICE, QUIT_CHOICE]
        client_auth = AuthReader.prompt_for_auth_method()
        assert client_auth is None
        captured = capsys.readouterr()
        invalid_option_error = '\nInvalid selection. Please choose from the following options:' \
                               '\n1. Admin User\n2. Authorized Service\n(q to quit)\n'
        assert invalid_option_error in captured.out
