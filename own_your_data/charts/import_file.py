import re

from duckdb import DuckDBPyConnection
from streamlit.runtime.uploaded_file_manager import UploadedFile

from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import timeit


def cleanup_db(duckdb_conn: DuckDBPyConnection):
    duckdb_conn.execute("drop table  if exists csv_import")
    duckdb_conn.execute("drop table  if exists csv_import_summary")
    duckdb_conn.execute("drop table  if exists csv_import_t")
    duckdb_conn.execute("drop table  if exists csv_import_summary_t")


def clean_column_name(column_name: str) -> str:
    return " ".join(re.sub("[^A-Za-z0-9 ]+", " ", column_name).title().split())


def import_csv(duckdb_conn: DuckDBPyConnection, data_source: UploadedFile):

    imported_data = duckdb_conn.read_csv(data_source, store_rejects=True)  # NOQA
    duckdb_conn.execute("create table csv_import as select * from imported_data")
    duckdb_conn.execute("create table csv_import_summary as SELECT * FROM (SUMMARIZE csv_import)")


def get_auto_column_expressions(duckdb_conn: DuckDBPyConnection) -> str:
    # from timestamp to date
    # from date to year, month name, day name

    date_related_columns = duckdb_conn.execute(
        """
        select column_name, case when column_type like 'TIMESTAMP%' then true else false end is_timestamp
        from csv_import_summary
        where column_type = 'DATE' or column_type like 'TIMESTAMP%'
        """
    ).fetchall()

    auto_column_expressions = [
        f"""
                monthname("{column[0]}") as "{clean_column_name(column_name=column[0])} Month Name Auto",
                dayname("{column[0]}") as "{clean_column_name(column_name=column[0])} Day Name Auto",
                date_part('year', "{column[0]}") as "{clean_column_name(column_name=column[0])} Year Auto"
        """
        for column in date_related_columns
    ]
    auto_column_expressions.extend(
        [
            f""" "{column[0]}"::date as "{clean_column_name(column_name=column[0])} Date Auto" """
            for column in date_related_columns
            if column[1]
        ]
    )
    return " ,".join(auto_column_expressions)


def finalize_import(duckdb_conn: DuckDBPyConnection, auto_column_expressions: str):

    column_selection = " ,".join(
        [
            f'"{column[0]}" as "{" ".join(re.sub("[^A-Za-z0-9 ]+", " ", column[0]).title().split())}"'
            for column in duckdb_conn.execute("select column_name from csv_import_summary").fetchall()
        ]
    )

    duckdb_conn.execute(
        f"""
        create table csv_import_t as
        select {column_selection}, {auto_column_expressions}
        from csv_import it
    """
    )

    duckdb_conn.execute("drop table csv_import")
    duckdb_conn.execute("drop table csv_import_summary")
    duckdb_conn.execute("create table csv_import_summary_t as SELECT * FROM (SUMMARIZE csv_import_t)")


@timeit
def import_csv_and_process_data(data_source: UploadedFile) -> DuckDBPyConnection:
    duckdb_conn = get_duckdb_conn()
    import_csv(duckdb_conn=duckdb_conn, data_source=data_source)
    auto_column_expressions = get_auto_column_expressions(duckdb_conn=duckdb_conn)
    finalize_import(duckdb_conn=duckdb_conn, auto_column_expressions=auto_column_expressions)
    return duckdb_conn
