import datetime

import streamlit as st
from code_editor import code_editor
from sqlparse import format as format_sql
from sqlparse import split as split_sql

from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import get_tables


def get_columns(table_name) -> list[str]:
    duckdb_conn = get_duckdb_conn()
    return [
        column[0]
        for column in duckdb_conn.execute(
            f"select column_name from duckdb_columns where table_name = '{table_name}' order by column_name"
        ).fetchall()
    ]


def get_data_summary(table_name):
    duckdb_conn = get_duckdb_conn()
    return duckdb_conn.execute(
        """
        select t.*
        from csv_import_summary_t t
        join duckdb_columns dc
        on t.column_name = dc.column_name
            and dc.table_name='csv_import_t'
        order by dc.column_index
    """
    ).df()


def get_data_analysis_components(table_name: str):
    duckdb_conn = get_duckdb_conn()

    preview_data_col, summary_data_col = st.columns(2)
    with preview_data_col.expander("Preview data"):
        st.info("This is a preview of the data, where maximum 3000 rows are displayed, in random order")
        st.dataframe(
            duckdb_conn.execute(f"from {table_name} limit 3000").df(),
            hide_index=True,
            height=200,
            use_container_width=True,
        )

    with summary_data_col.expander("Summary of the data"):
        st.info("This is a summary of the data, containing statistics")
        st.dataframe(
            duckdb_conn.execute(f"summarize {table_name}").df(),
            hide_index=True,
            height=200,
            use_container_width=True,
        )


def get_code_editor(code_page):

    if code_page not in st.session_state:
        st.info("again")
        st.session_state[code_page] = "-- write your SQL here"

    warning_col, button_col = st.columns([9, 1])

    warning_col.warning(
        "The SQL code you are writing is not automatically saved (it is on the save and execute actions).\
        Keep in mind that the code written below is lost once you close the browser,\
        make sure to download it if needed."
    )
    button_col.download_button(
        "Download code",
        data=format_sql(st.session_state[code_page]),
        file_name=f"own_your_data_code_{datetime.datetime.now().isoformat()}.sql",
    )
    execution_buttons = [
        {
            "name": "copy",
            "feather": "Copy",
            "hasText": True,
            "alwaysOn": True,
            "commands": ["copyAll"],
            "style": {"top": "0rem", "right": "0.4rem"},
        },
        {
            "name": "execute",
            "feather": "Send",
            "primary": True,
            "hasText": True,
            "alwaysOn": True,
            "commands": ["save-state", "submit"],
            "style": {"bottom": "0rem", "right": "0.4rem"},
        },
        {
            "name": "save",
            "feather": "Save",
            "hasText": True,
            "alwaysOn": True,
            "commands": ["save-state", ["response", "saved"]],
            "response": "saved",
            "style": {"top": "0rem", "right": "5rem"},
        },
    ]
    sql_editor = code_editor(
        st.session_state[code_page],
        lang="sql",
        buttons=execution_buttons,
        completions=[{"caption": table, "value": table} for table in get_tables()],
    )

    if sql_editor.get("type") == "saved":
        sql_query = sql_editor.get("text")
        st.session_state[code_page] = sql_query

    if sql_editor.get("type") == "submit":
        sql_query = sql_editor.get("text")
        st.session_state[code_page] = sql_query
        duckdb_conn = get_duckdb_conn()
        for statement in split_sql(sql_editor.get("selected") or sql_query):
            try:
                st.dataframe(duckdb_conn.execute(statement).df(), hide_index=True, height=200, use_container_width=True)
            except Exception as error:
                st.error(error)
        st.session_state.table_options = get_tables()
        st.session_state.index_option = None
