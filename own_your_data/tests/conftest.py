import pytest

from own_your_data.utils import get_duckdb_conn


@pytest.fixture(scope="session")
def duckdb_conn():
    return get_duckdb_conn()
