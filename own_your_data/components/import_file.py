import re

import streamlit
from streamlit.runtime.uploaded_file_manager import UploadedFile

from own_your_data.charts.helpers import get_order_clause
from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import timeit


@streamlit.cache_resource
def cleanup_db(file_id):
    duckdb_conn = get_duckdb_conn()
    duckdb_conn.execute("drop table  if exists csv_import")
    duckdb_conn.execute("drop table  if exists csv_import_t")
    duckdb_conn.execute("drop table  if exists csv_import_summary_t")


def clean_column_name(column_name: str) -> str:
    return " ".join(re.sub("[^A-Za-z0-9 ]+", " ", column_name).title().split())


@timeit
@streamlit.cache_resource
def import_uploaded_file(data_source: UploadedFile, file_id):
    duckdb_conn = get_duckdb_conn()
    imported_data = duckdb_conn.read_csv(data_source, store_rejects=True)  # NOQA
    duckdb_conn.execute("create table csv_import as select * from imported_data")


def get_auto_column_expressions() -> list[str]:
    # from timestamp to date
    # from date to year, month name, day name
    duckdb_conn = get_duckdb_conn()
    date_related_columns = duckdb_conn.execute(
        """
        select column_name, case when data_type like 'TIMESTAMP%' then true else false end is_timestamp
        from duckdb_columns
        where table_name='csv_import'
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


def finalize_import(auto_column_expressions: list[str]):
    duckdb_conn = get_duckdb_conn()
    column_selection = [
        f'"{column[0]}" as "{" ".join(re.sub("[^A-Za-z0-9 ]+", " ", column[0]).title().split())}"'
        for column in duckdb_conn.execute(
            "select column_name from duckdb_columns where table_name='csv_import'"
        ).fetchall()
    ]
    column_selection.extend(auto_column_expressions)

    duckdb_conn.execute(
        f"""
        create table csv_import_t as
        select {','.join(column_selection)}
        from csv_import it
    """
    )

    unique_values_query = " union all ".join(
        [
            f"""select '{column[0]}' as column_name,
                array_agg(distinct "{column[0]}" order by {get_order_clause(column[0])}) as unique_value
                from csv_import_t
            """
            for column in duckdb_conn.execute(
                "select column_name from duckdb_columns where table_name='csv_import_t'"
            ).fetchall()
        ]
    )

    duckdb_conn.execute(
        f"""create table csv_import_summary_t as
            with unique_values_cte as (
                {unique_values_query}
            )
                select t.* , string_agg(uvc.unique_value[:50], ',') as first_50_unique_values
                from (SUMMARIZE csv_import_t) t
                    left join unique_values_cte uvc on t.column_name = uvc.column_name
                group by all
    """
    )

    duckdb_conn.execute("drop table csv_import")


@timeit
@streamlit.cache_resource
def process_file(file_id):
    auto_column_expressions = get_auto_column_expressions()
    finalize_import(auto_column_expressions=auto_column_expressions)
