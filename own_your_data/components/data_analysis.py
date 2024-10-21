import streamlit as st

from own_your_data.utils import get_duckdb_conn


def get_columns(table_name) -> list[str]:
    duckdb_conn = get_duckdb_conn()
    return [
        column[0]
        for column in duckdb_conn.execute(
            f"select column_name from duckdb_columns where table_name = '{table_name}' order by column_name"
        ).fetchall()
    ]


def get_data_analysis_components(table_name: str):
    duckdb_conn = get_duckdb_conn()

    preview_data_col, summary_data_col = st.columns(2)
    with preview_data_col.expander("Preview data", expanded=True):
        st.info("This is a preview of the data, where maximum 3000 rows are displayed, in random order")
        st.dataframe(
            duckdb_conn.execute(f"from {table_name} limit 3000").df(),
            hide_index=True,
            height=200,
            use_container_width=True,
        )

    with summary_data_col.expander("Summary of the data", expanded=True):
        st.info("This is a summary of the data, containing statistics")
        st.dataframe(
            duckdb_conn.execute(f"summarize {table_name}").df(),
            hide_index=True,
            height=200,
            use_container_width=True,
        )
