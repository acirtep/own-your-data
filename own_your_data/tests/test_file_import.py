import uuid
from io import BytesIO
from pathlib import Path
from unittest import mock

import duckdb
import pytest

from own_your_data.components.import_file import finalize_import
from own_your_data.components.import_file import get_auto_column_expressions
from own_your_data.components.import_file import import_uploaded_file

test_file_path = f"{Path(__file__).parent}/test_csv.csv"


@pytest.fixture
def duckdb_conn():
    return duckdb.connect()


@pytest.fixture()
def file_id():
    return uuid.uuid4()


@pytest.fixture
def duckdb_conn_with_initial_csv_data(duckdb_conn, file_id):
    with mock.patch("own_your_data.components.import_file.get_duckdb_conn", return_value=duckdb_conn):
        with open(test_file_path, "r") as f:
            import_uploaded_file(data_source=BytesIO(f.read().encode()), file_id=file_id)
        return duckdb_conn


def test_import_file(duckdb_conn, file_id):
    with mock.patch("own_your_data.components.import_file.get_duckdb_conn", return_value=duckdb_conn):
        with open(test_file_path, "r") as f:
            import_uploaded_file(data_source=BytesIO(f.read().encode()), file_id=file_id)

    assert duckdb_conn.sql("select * from csv_import")


def test_get_auto_column_expressions(duckdb_conn_with_initial_csv_data):
    with mock.patch(
        "own_your_data.components.import_file.get_duckdb_conn", return_value=duckdb_conn_with_initial_csv_data
    ):
        auto_column_expressions = ",".join(get_auto_column_expressions())
    assert 'monthname("register_date") as "Register Date Month Name Auto"' in auto_column_expressions
    assert 'dayname("register_date") as "Register Date Day Name Auto"' in auto_column_expressions
    assert 'date_part(\'year\', "register_date") as "Register Date Year Auto"' in auto_column_expressions
    assert '"register_date"::date as "Register Date Date Auto"' in auto_column_expressions


def test_finalize_import(duckdb_conn_with_initial_csv_data):
    with mock.patch(
        "own_your_data.components.import_file.get_duckdb_conn", return_value=duckdb_conn_with_initial_csv_data
    ):
        auto_column_expressions = get_auto_column_expressions()
        finalize_import(auto_column_expressions=auto_column_expressions)

    with pytest.raises(duckdb.CatalogException):
        duckdb_conn_with_initial_csv_data.sql("select * from csv_import")

    assert duckdb_conn_with_initial_csv_data.sql("select * from csv_import_t")
    assert duckdb_conn_with_initial_csv_data.sql("select * from csv_import_summary_t")
    assert duckdb_conn_with_initial_csv_data.sql(
        "select * from csv_import_summary_t where first_50_unique_values is not null"
    )
