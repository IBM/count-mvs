#! /usr/bin/env python

from mock import patch
from countMVS import TimePeriodReader


def test_default_period_used_when_enter_pressed():
    with patch('six.moves.input') as mock_input:
        mock_input.return_value = None
        selection = TimePeriodReader.prompt_for_time_period(1, 10)
        mock_input.assert_called_with('Please enter your choice in days (default {} [Enter], max {}): '.format(1, 10))
        assert selection == 1


def test_valid_selection_returned():
    with patch('six.moves.input') as mock_input:
        mock_input.return_value = 2
        selection = TimePeriodReader.prompt_for_time_period(1, 10)
        mock_input.assert_called_with('Please enter your choice in days (default {} [Enter], max {}): '.format(1, 10))
        assert selection == 2


def test_invalid_min_range_selection(capsys):
    with patch('six.moves.input') as mock_input:
        mock_input.side_effect = [-1, 3]
        selection = TimePeriodReader.prompt_for_time_period(1, 10)
        assert selection == 3
        captured = capsys.readouterr()
        assert 'Invalid selection. You can only select a minimum of 1 day' in captured.out


def test_invalid_max_range_selection(capsys):
    with patch('six.moves.input') as mock_input:
        mock_input.side_effect = [11, 3]
        selection = TimePeriodReader.prompt_for_time_period(1, 10)
        assert selection == 3
        captured = capsys.readouterr()
        invalid_option_error = 'Invalid selection. You can only select up to a maximum of {} days'.format(10)
        assert invalid_option_error in captured.out


def test_invalid_return_type_selection(capsys):
    with patch('six.moves.input') as mock_input:
        mock_input.side_effect = ["test", 4]
        selection = TimePeriodReader.prompt_for_time_period(1, 10)
        assert selection == 4
        captured = capsys.readouterr()
        invalid_option_error = 'Invalid selection. You must enter a numeric value'
        assert invalid_option_error in captured.out
