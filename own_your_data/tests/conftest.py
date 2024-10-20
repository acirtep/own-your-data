from unittest import mock

import duckdb
import pytest

from own_your_data.utils import initial_load


@pytest.fixture(scope="session")
def duckdb_conn():
    duckdb_conn = duckdb.connect()
    with mock.patch("own_your_data.utils.get_duckdb_conn", return_value=duckdb_conn):
        initial_load()
    return duckdb_conn
