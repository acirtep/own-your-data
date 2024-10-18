import streamlit as st
from code_editor import code_editor
from sqlparse import split as split_sql

from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import get_tables


@st.cache_resource(hash_funcs={dict: lambda response: response.get("id")})
def execute_sql(sql_editor):
    if sql_editor.get("type") == "submit":
        sql_query = sql_editor.get("text")
        duckdb_conn = get_duckdb_conn()
        for statement in split_sql(sql_editor.get("selected") or sql_query):
            try:
                st.dataframe(duckdb_conn.execute(statement).df(), hide_index=True, height=200, use_container_width=True)
            except Exception as error:
                st.error(error)

        st.session_state.table_options = get_tables()


def display_duckdb_catalog():
    st.subheader("Data Catalogue")
    search = st.text_input("Search for a table or column")
    duckdb_conn = get_duckdb_conn()
    if not search:
        for table in st.session_state.table_options:
            with st.expander(table):
                for col in duckdb_conn.execute(
                    f"select column_name from duckdb_columns where table_name = '{table}'"
                ).fetchall():
                    st.markdown(f"- {col[0]}")
    else:
        for table in duckdb_conn.execute(
            f"""
            select distinct table_name
                from duckdb_columns
            where column_name ilike '%{search}%' or table_name ilike '%{search}%'
        """
        ).fetchall():
            with st.expander(table[0]):
                for col in duckdb_conn.execute(
                    f"select column_name from duckdb_columns where table_name = '{table[0]}'"
                ).fetchall():
                    st.markdown(f"- {col[0]}")


def get_code_editor():
    st.subheader("Code Editor")
    #
    # _, button_col = st.columns([10, 1])
    #
    # button_col.download_button(
    #     "Download code",
    #     data=format_sql(st.session_state.code_text),
    #     file_name=f"own_your_data_code_{datetime.datetime.now().isoformat()}.sql",
    # )

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
    ]
    sql_editor = code_editor(
        code="-- write your SQL here \n-- there is no limit added to select statements \n",
        lang="sql",
        buttons=execution_buttons,
        completions=[{"caption": table, "value": table} for table in st.session_state.table_options],
        allow_reset=True,
        key="sql-editor",
    )

    execute_sql(sql_editor)
