from io import BytesIO
from pathlib import Path

import duckdb
import pytest

from own_your_data.database.helpers import finalize_import
from own_your_data.database.helpers import get_auto_column_expressions
from own_your_data.database.helpers import import_csv

test_file_path = f"{Path(__file__).parent}/test_csv.csv"


@pytest.fixture()
def duckdb_conn():
    return duckdb.connect()


@pytest.fixture
def duckdb_conn_with_initial_csv_data(duckdb_conn):
    with open(test_file_path, "r") as f:
        import_csv(duckdb_conn=duckdb_conn, data_source=BytesIO(f.read().encode()))
    return duckdb_conn


def test_import_csv(duckdb_conn):
    with open(test_file_path, "r") as f:
        import_csv(duckdb_conn=duckdb_conn, data_source=BytesIO(f.read().encode()))

    assert duckdb_conn.sql("select * from csv_import")
    assert duckdb_conn.sql("select * from csv_import_summary")


def test_get_auto_column_expressions(duckdb_conn_with_initial_csv_data):
    auto_column_expressions = get_auto_column_expressions(duckdb_conn=duckdb_conn_with_initial_csv_data)
    assert 'monthname("register_date") as "Register Date Month Name Auto"' in auto_column_expressions
    assert 'dayname("register_date") as "Register Date Day Name Auto"' in auto_column_expressions
    assert 'date_part(\'year\', "register_date") as "Register Date Year Auto"' in auto_column_expressions
    assert '"register_date"::date as "Register Date Date Auto"' in auto_column_expressions


def test_finalize_import(duckdb_conn_with_initial_csv_data):
    auto_column_expressions = get_auto_column_expressions(duckdb_conn=duckdb_conn_with_initial_csv_data)
    finalize_import(duckdb_conn=duckdb_conn_with_initial_csv_data, auto_column_expressions=auto_column_expressions)

    with pytest.raises(duckdb.CatalogException):
        duckdb_conn_with_initial_csv_data.sql("select * from csv_import")
        duckdb_conn_with_initial_csv_data.sql("select * from csv_import_summary")

    assert duckdb_conn_with_initial_csv_data.sql("select * from csv_import_t")
    assert duckdb_conn_with_initial_csv_data.sql("select * from csv_import_summary_t")
