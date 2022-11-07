#! /usr/bin/env python

import re
from countMVS import ProgressUtils


def test_progress_bar_at_zero(capsys):
    ProgressUtils.print_progress_bar(0)
    captured = capsys.readouterr()
    assert re.match(r"\rProcessing.*[|]\s0%$", captured.out)


def test_progress_bar_at_one_hundred(capsys):
    ProgressUtils.print_progress_bar(100)
    captured = capsys.readouterr()
    assert re.match(r"\rProcessing.*[|]\s100%\s...done\n\n$", captured.out)


def test_progress_bar_at_fifty(capsys):
    ProgressUtils.print_progress_bar(50)
    captured = capsys.readouterr()
    assert re.match(r"\rProcessing.*[|]\s50%$", captured.out)


def test_progress_bar_at_greater_than_limit(capsys):
    ProgressUtils.print_progress_bar(101)
    captured = capsys.readouterr()
    assert re.match(r"\rProcessing.*[|]\s100%\s...done\n\n$", captured.out)


def test_progress_bar_at_below_zero(capsys):
    ProgressUtils.print_progress_bar(-1)
    captured = capsys.readouterr()
    assert re.match(r"\rProcessing.*[|]\s0%$", captured.out)
