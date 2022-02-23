"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

from os.path import exists

LOG_FILE = '/var/log/countMVS.log'


def print_count_mvs_log():
    # print the countMVS.log to help with debugging
    if exists(LOG_FILE):
        with open('/var/log/countMVS.log', 'r') as file:
            for line in file:
                print(line, sep='')
