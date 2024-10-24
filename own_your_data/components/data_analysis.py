import streamlit as st

from own_your_data.utils import cache_duckdb_execution
from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import timeit


def get_columns(table_name) -> list[str]:
    duckdb_conn = get_duckdb_conn()
    return [
        column[0]
        for column in duckdb_conn.execute(
            f"select column_name from duckdb_columns where table_name = '{table_name}' order by column_name"
        ).fetchall()
    ]


@timeit
def get_data_analysis_components(table_name: str):
    duckdb_conn = get_duckdb_conn()

    with st.expander("A preview of the data"):
        preview_data_col, summary_data_col = st.columns(2)
        preview_data_col.info("This is a preview of the data, where maximum 100 rows are displayed, in random order")
        preview_data_col.dataframe(
            cache_duckdb_execution(_duckdb_conn=duckdb_conn, sql_query=f"from {table_name} limit 100"),
            hide_index=True,
            height=200,
            use_container_width=True,
        )

        summary_data_col.info("This is a summary of the data, containing statistics")
        summary_data_col.dataframe(
            cache_duckdb_execution(_duckdb_conn=duckdb_conn, sql_query=f"summarize {table_name}"),
            hide_index=True,
            height=200,
            use_container_width=True,
        )
