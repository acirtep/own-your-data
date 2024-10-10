import streamlit as st

from own_your_data.utils import get_duckdb_conn


@st.cache_data
def get_columns(file_id) -> list[str]:
    duckdb_conn = get_duckdb_conn()
    return [
        column[0]
        for column in duckdb_conn.execute(
            "select column_name from csv_import_summary_t order by column_name"
        ).fetchall()
    ]


@st.cache_data
def get_data_summary(file_id):
    duckdb_conn = get_duckdb_conn()
    return duckdb_conn.execute("select * from csv_import_summary_t order by column_name").df()


@st.cache_data
def get_data_preview(file_id):
    duckdb_conn = get_duckdb_conn()
    return duckdb_conn.execute("select * from csv_import_t limit 3000").df()


def get_data_analysis_components(file_id):
    columns = get_columns(file_id)

    if len(columns) < 2:
        st.error("There needs to be at least 2 columns in the file!")

    else:
        with st.expander("Preview data (max 3000)"):
            st.dataframe(get_data_preview(file_id), hide_index=True, height=200)

        with st.expander("Data summary"):
            st.dataframe(
                get_data_summary(file_id),
                hide_index=True,
                height=200,
            )
