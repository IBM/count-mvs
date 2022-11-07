#! /usr/bin/env python

from countMVS import TextFormatter


def test_format_text_bold():
    formatter = TextFormatter()
    assert formatter.bold("test") == '{}{}{}'.format(TextFormatter.BOLD_ANSI_ESCAPE_CODE, "test",
                                                     TextFormatter.NORMAL_ANSI_ESCAPE_CODE)
