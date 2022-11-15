from mock import patch, Mock
from countMVS import Auth, MVSProcessor, PermissionCheckResult, QuitSelected


def test_not_running_on_console(capsys):
    with patch('countMVS.Validator.is_console', return_value=False), \
         patch('countMVS.MVSProcessor._close_db_connection') as mock_db_closed, \
         patch('countMVS.MVSProcessor._parse_arguments', return_value={}):
        processor = MVSProcessor()
        exit_code = processor.run()
        captured = capsys.readouterr()
        assert exit_code == 1
        assert captured.out == 'This script can only be ran on the console. Exiting...\n'
        mock_db_closed.assert_called()


def test_keyboard_interrupt(capsys):
    with patch('countMVS.Validator.is_console', return_value=True), \
         patch('countMVS.MVSProcessor._generate_mvs_results', side_effect=KeyboardInterrupt), \
         patch('countMVS.MVSProcessor._parse_arguments', return_value={}):
        processor = MVSProcessor()
        exit_code = processor.run()
        captured = capsys.readouterr()
        assert exit_code == 1
        assert captured.out == '\nExiting...\n'


def test_quit_selected():
    with patch('countMVS.Validator.is_console', return_value=True), \
         patch('countMVS.MVSProcessor._generate_mvs_results', side_effect=QuitSelected), \
         patch('countMVS.MVSProcessor._parse_arguments', return_value={}):
        processor = MVSProcessor()
        exit_code = processor.run()
        assert exit_code == 0


def test_permissions_check(capsys):
    mock_aql_client = Mock()
    mock_permission_check_result = Mock()
    mock_permission_check_result.is_successful.return_value = False
    mock_permission_check_result.get_error_message.return_value = 'Test Error'
    with patch('countMVS.Validator.is_console', return_value=True), \
         patch('countMVS.Validator.perform_api_permission_check', return_value=mock_permission_check_result), \
         patch('countMVS.MVSProcessor._store_period_in_days'), \
         patch('countMVS.MVSProcessor._parse_arguments', return_value={}):
        processor = MVSProcessor(aql_client=mock_aql_client)
        exit_code = processor.run()
        captured = capsys.readouterr()
        assert exit_code == 1
        assert captured.out == 'Test Error\n'


def test_clients_initialized(capsys):
    with patch('countMVS.AuthReader') as mock_auth_reader, \
         patch('countMVS.TimePeriodReader') as mock_time_period_reader, \
         patch('countMVS.Validator') as mock_validator, \
         patch('countMVS.MyVer') as mock_my_ver, \
         patch('countMVS.DatabaseClient'), \
         patch('countMVS.DatabaseService.get_domain_count',return_value=1), \
         patch('countMVS.DatabaseService.build_log_source_map',return_value={}), \
         patch('countMVS.MVSProcessor._parse_arguments',return_value={}):
        mock_auth = Auth()
        mock_auth.set_password('test')
        mock_permission_check_result = PermissionCheckResult(mock_auth)
        mock_time_period_reader.prompt_for_time_period.return_value = 3
        mock_auth_reader.prompt_for_auth_method.return_value = mock_auth
        mock_validator.is_console.return_value = True
        mock_validator.perform_api_permission_check.return_value = mock_permission_check_result
        mock_my_ver.hostname.return_value = 'test'
        processor = MVSProcessor()
        exit_code = processor.run()
        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out == 'MVS count for the deployment is 0\n'
