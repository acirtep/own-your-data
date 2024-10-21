from io import BytesIO
from pathlib import Path
from unittest import mock

import pytest
from duckdb import CatalogException

from own_your_data.components.import_file import cleanup_db
from own_your_data.components.import_file import get_auto_column_expressions
from own_your_data.components.import_file import import_uploaded_file
from own_your_data.components.import_file import process_imported_data

test_file_path = f"{Path(__file__).parent}/test_csv.csv"


@pytest.fixture(scope="module")
def table_name():
    return "test_import_table_name"


@pytest.fixture(scope="module")
def final_table_name(table_name):
    return f"{table_name}_t"


@pytest.fixture(scope="module", autouse=True)
def duckdb_conn_with_initial_csv_data(duckdb_conn, table_name):
    with mock.patch("own_your_data.components.import_file.get_duckdb_conn", return_value=duckdb_conn):
        with open(test_file_path, "r") as f:
            import_uploaded_file(
                data_source=BytesIO(f.read().encode()),
                table_name=table_name,
                file_name="test_csv.csv",
            )
        return duckdb_conn


def test_import_file(duckdb_conn, table_name):
    with mock.patch("own_your_data.components.import_file.get_duckdb_conn", return_value=duckdb_conn):
        cleanup_db(table_name)
        with open(test_file_path, "r") as f:
            import_uploaded_file(
                data_source=BytesIO(f.read().encode()),
                table_name=table_name,
                file_name="test_csv.csv",
            )

    assert duckdb_conn.sql(f"select * from {table_name}")


def test_get_auto_column_expressions(duckdb_conn_with_initial_csv_data, table_name):
    with mock.patch(
        "own_your_data.components.import_file.get_duckdb_conn", return_value=duckdb_conn_with_initial_csv_data
    ):
        auto_column_expressions = ",".join(get_auto_column_expressions(table_name=table_name))
    assert 'monthname("register_date") as "Register Date Month Name Auto"' in auto_column_expressions
    assert 'dayname("register_date") as "Register Date Day Name Auto"' in auto_column_expressions
    assert 'date_part(\'year\', "register_date") as "Register Date Year Auto"' in auto_column_expressions
    assert '"register_date"::date as "Register Date Date Auto"' in auto_column_expressions


def test_process_imported_data(duckdb_conn_with_initial_csv_data, table_name, final_table_name):
    with mock.patch(
        "own_your_data.components.import_file.get_duckdb_conn", return_value=duckdb_conn_with_initial_csv_data
    ):
        process_imported_data(table_name)

    with pytest.raises(CatalogException):
        duckdb_conn_with_initial_csv_data.sql(f"select * from {table_name}")

    assert duckdb_conn_with_initial_csv_data.sql(f"select * from {final_table_name}")
