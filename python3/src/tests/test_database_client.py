#! /usr/bin/env python

import pytest
from mock import Mock, patch
from psycopg2.extras import RealDictCursor
from countMVS import DatabaseClient, DatabaseService, TooManyResultsError

DB_NAME = 'qradar'
DB_USER = 'qradar'
COUNT_COLUMN_NAME = 'count'


def build_mock_cursor(row_count, mock_cursor_with=None, response=None, execute_return_value=True):
    mock_cursor = Mock()
    mock_cursor.rowcount = row_count
    if response:
        mock_cursor.fetchone.return_value = response
    if mock_cursor_with:
        mock_cursor_with.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor_with.__exit__ = Mock(return_value=None)
    if row_count == 0:
        mock_cursor.fetchall.return_value = []
    if execute_return_value:
        mock_cursor.execute.return_value = execute_return_value
    return mock_cursor


def build_mock_conn(mock_cursor_with=None, close_return_value=None):
    mock_conn = Mock()
    if mock_cursor_with:
        mock_conn.cursor.return_value = mock_cursor_with
    if close_return_value:
        mock_conn.close.return_value = close_return_value
    return mock_conn


def test_connect_to_db():
    db_client = DatabaseClient(DB_NAME, DB_USER)
    with patch('psycopg2.connect') as mock_pg_connect:
        db_client.connect()
        mock_pg_connect.assert_called_with(database=DB_NAME, user=DB_USER, cursor_factory=RealDictCursor)


def test_fetch_one_with_one_result():
    db_client = DatabaseClient(DB_NAME, DB_USER)
    with patch('psycopg2.connect') as mock_pg_connect:
        mock_cursor_with = Mock()
        mock_pg_connect.return_value = build_mock_conn(mock_cursor_with)
        mock_cursor = build_mock_cursor(1, mock_cursor_with, {COUNT_COLUMN_NAME: 4})
        db_client.connect()
        db_result = db_client.fetch_one(DatabaseService.DOMAIN_COUNT_QUERY)
        mock_cursor.execute.assert_called_with(DatabaseService.DOMAIN_COUNT_QUERY)
        mock_cursor.fetchone.assert_called_once()
        assert db_result[COUNT_COLUMN_NAME] == 4


def test_fetch_one_with_more_than_one_result():
    db_client = DatabaseClient(DB_NAME, DB_USER)
    with patch('psycopg2.connect') as mock_pg_connect:
        mock_cursor_with = Mock()
        mock_pg_connect.return_value = build_mock_conn(mock_cursor_with)
        mock_cursor = build_mock_cursor(3, mock_cursor_with)
        db_client.connect()
        with pytest.raises(TooManyResultsError) as exception:
            db_client.fetch_one(DatabaseService.DOMAIN_COUNT_QUERY)
        mock_cursor.execute.assert_called_with(DatabaseService.DOMAIN_COUNT_QUERY)
        assert 'Too many rows returned' in str(exception)


def test_fetch_all():
    db_client = DatabaseClient(DB_NAME, DB_USER)
    with patch('psycopg2.connect') as mock_pg_connect:
        mock_cursor_with = Mock()
        mock_pg_connect.return_value = build_mock_conn(mock_cursor_with)
        mock_cursor = build_mock_cursor(0, mock_cursor_with)
        db_client.connect()
        db_result = db_client.fetch_all(DatabaseService.LOG_SOURCE_RETRIEVAL_QUERY)
        mock_cursor.execute.assert_called_with(DatabaseService.LOG_SOURCE_RETRIEVAL_QUERY)
        assert db_result == []
        mock_cursor.fetchall.assert_called_once()


def test_close_db_conn():
    db_client = DatabaseClient(DB_NAME, DB_USER)
    with patch('psycopg2.connect') as mock_pg_connect:
        mock_conn = build_mock_conn(close_return_value=True)
        mock_pg_connect.return_value = mock_conn
        db_client.connect()
        db_client.close()
        mock_conn.close.assert_called_once()
