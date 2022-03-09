"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import pexpect


def test_run_on_non_console_host(pyversion):
    process = pexpect.spawn(f'/bin/bash -c "MVS_IS_CONSOLE=false python{pyversion} countMVS.py"')
    process.expect(pexpect.EOF, timeout=5)

    output_lines = process.before.decode("utf-8").split("\n")
    process.close()
    output_lines = [x.strip() for x in output_lines if x]

    assert process.exitstatus == 1
    assert output_lines[0] == "Running on host that is not console. Exiting."
