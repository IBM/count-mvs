#! /usr/bin/env python

from socket import gaierror
from testfixtures import LogCapture
from mock import patch
from countMVS import MachineIdentifierParser, IPParser

DUMMY_IP = '1.1.1.1'
DUMMY_HOSTNAME = 'test.com'
DUMMY_ERROR = 'Exception'


def test_url_parsed_as_ip():
    parser = MachineIdentifierParser()
    machine_identifier_from_url = parser.parse_machine_identifier('https://{}'.format(DUMMY_IP))
    machine_identifier_ip = parser.parse_machine_identifier(DUMMY_IP)
    assert machine_identifier_from_url == DUMMY_IP and machine_identifier_ip == DUMMY_IP


def test_ip_parsed_for_hostname():
    with patch('socket.gethostbyname', return_value=DUMMY_IP):
        parser = IPParser()
        device_ip = parser.get_device_ip(DUMMY_HOSTNAME)
        assert device_ip == DUMMY_IP


def test_parser_exception_returns_none():
    with LogCapture() as captured:
        with patch('socket.gethostbyname', side_effect=gaierror(DUMMY_ERROR)):
            parser = IPParser()
            device_ip = parser.get_device_ip(DUMMY_HOSTNAME)
            assert device_ip is None
            assert captured.records[0].getMessage() == 'Unable to resolve hostname {} to IP, Reason [{}]'.format(
                DUMMY_HOSTNAME, DUMMY_ERROR)
