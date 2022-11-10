#! /usr/bin/env python

import json
import os
from countMVS import APIError, ArielSearch, LogSource

TEST_DIR = os.path.dirname(__file__)
RESPONSES_DIR = 'responses'
DB_ROWS_DIR = 'dbrows'


def read_response_from_file(filename):
    with open(os.path.join(TEST_DIR, RESPONSES_DIR, filename)) as json_file:
        response_json = json.load(json_file)
        return response_json


def read_db_row_from_file(filename):
    with open(os.path.join(TEST_DIR, DB_ROWS_DIR, filename)) as json_file:
        row = json.load(json_file)
        return row


def read_db_rows_from_file(filename):
    with open(os.path.join(TEST_DIR, DB_ROWS_DIR, filename)) as json_file:
        rows = json.load(json_file)
        if isinstance(rows, list):
            return rows
        return [rows]


def build_log_source(json_file):
    log_source_data = read_db_row_from_file(json_file)
    return LogSource.from_json(log_source_data)


def build_log_sources(json_file):
    log_sources = []
    log_source_data = read_db_rows_from_file(json_file)
    for log_source_entry in log_source_data:
        log_sources.append(LogSource.from_json(log_source_entry))
    return log_sources


def build_ariel_search(json_file):
    ariel_search_data = read_response_from_file(json_file)
    return ArielSearch.from_json(ariel_search_data)


def build_ariel_search_results(json_file):
    return read_response_from_file(json_file)


def build_api_error(json_file):
    api_error_data = read_response_from_file(json_file)
    return APIError.from_json(api_error_data)
