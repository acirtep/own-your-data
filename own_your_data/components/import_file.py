import re
from io import BytesIO
from pathlib import Path
from typing import IO
from zipfile import ZipFile

from streamlit.runtime.uploaded_file_manager import UploadedFile

from own_your_data.utils import gather_database_size
from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import timeit


@gather_database_size
def cleanup_db(table_name):
    duckdb_conn = get_duckdb_conn()
    duckdb_conn.execute(f"drop table  if exists {table_name}")


def clean_column_name(column_name: str) -> str:
    return " ".join(re.sub("[^A-Za-z0-9 ]+", " ", column_name).title().split())


def get_table_name(file_name: str) -> str:
    cleaned_table_name = "_".join(re.sub("[^A-Za-z0-9 ]+", " ", file_name).split())
    return f"file_{cleaned_table_name.lower()}"


@timeit
def get_unzipped_data(data_source: UploadedFile) -> list[IO[bytes]]:
    with ZipFile(data_source) as imported_zip:
        return [imported_zip.open(file) for file in imported_zip.namelist() if file.endswith((".csv", ".txt"))]


@timeit
@gather_database_size
def import_uploaded_file(data_source: list[UploadedFile] | list[IO[bytes]], table_name, file_name):
    duckdb_conn = get_duckdb_conn()
    imported_data = duckdb_conn.read_csv(data_source)  # NOQA
    duckdb_conn.execute(f"create table {table_name} as select * from imported_data")

    duckdb_conn.execute(
        f"""
        insert into file_import_metadata
        (file_name, table_name, start_import_datetime)
            values
        ('{file_name}', '{table_name}_t', current_timestamp)
    """
    )


def get_auto_column_expressions(table_name) -> list[str]:
    # from timestamp to date
    # from date to year, month name, day name
    duckdb_conn = get_duckdb_conn()
    date_related_columns = duckdb_conn.execute(
        f"""
        select column_name, case when data_type like 'TIMESTAMP%' then true else false end is_timestamp
        from duckdb_columns
        where table_name='{table_name}'
        and (data_type = 'DATE' or data_type like 'TIMESTAMP%')
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
    return auto_column_expressions


@timeit
@gather_database_size
def process_imported_data(table_name):
    duckdb_conn = get_duckdb_conn()
    auto_column_expressions = get_auto_column_expressions(table_name=table_name)
    column_selection = [
        f'"{column[0]}" as "{" ".join(re.sub("[^A-Za-z0-9 ]+", " ", column[0]).title().split())}"'
        for column in duckdb_conn.execute(
            f"select column_name from duckdb_columns where table_name='{table_name}'"
        ).fetchall()
    ]
    column_selection.extend(auto_column_expressions)

    duckdb_conn.execute(
        f"""
        create table {table_name}_t as
        select {','.join(column_selection)}
        from {table_name} it
    """
    )

    duckdb_conn.execute(
        f"""
        update file_import_metadata
            set end_import_datetime = current_timestamp
        where table_name = '{table_name}_t'
        and id = (select max(id) from file_import_metadata where table_name = '{table_name}_t')
    """
    )

    #
    # unique_values_query = " union all ".join(
    #     [
    #         f"""select '{column[0]}' as column_name,
    #             array_agg(distinct "{column[0]}" order by {get_order_clause(column[0])}) as unique_value
    #             from csv_import_t
    #         """
    #         for column in duckdb_conn.execute(
    #             "select column_name from duckdb_columns where table_name='csv_import_t'"
    #         ).fetchall()
    #     ]
    # )
    #
    # duckdb_conn.execute(
    #     f"""create table csv_import_summary_t as
    #         with unique_values_cte as (
    #             {unique_values_query}
    #         )
    #             select t.* , string_agg(uvc.unique_value[:50], ',') as first_50_unique_values
    #             from (SUMMARIZE csv_import_t) t
    #                 left join unique_values_cte uvc on t.column_name = uvc.column_name
    #             group by all
    # """
    # )
    #
    duckdb_conn.execute(f"drop table {table_name}")


def import_demo_file():
    with open(f"{Path(__file__).parent.parent}/demo/demo_file.txt", "r") as demo_file:
        table_name = get_table_name("demo_file.txt")
        cleanup_db(table_name=f"{table_name}_t")
        import_uploaded_file(
            data_source=BytesIO(demo_file.read().encode()),
            table_name=table_name,
            file_name="demo_file.txt",
        )
        process_imported_data(table_name=table_name)
