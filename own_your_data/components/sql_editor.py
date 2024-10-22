import datetime

import streamlit as st
from code_editor import code_editor
from duckdb.duckdb import FatalException
from duckdb.duckdb import InternalException
from sqlparse import format as format_sql
from sqlparse import parse
from sqlparse.sql import Identifier

from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import get_tables
from own_your_data.utils import insert_database_size


@st.cache_resource(hash_funcs={dict: lambda response: response.get("id")})
def execute_sql(sql_editor):
    if sql_editor.get("type") == "submit":
        sql_query = sql_editor.get("text")
        duckdb_conn = get_duckdb_conn()
        for statement in parse(sql_editor.get("selected") or sql_query):
            if statement.get_type() in ["DROP", "ALTER"]:
                table_name = [a.get_name() for a in statement.get_sublists() if isinstance(a, Identifier)]
                if list(
                    {"file_import_metadata", "calendar_t", "database_size_monitoring"}.intersection(set(table_name))
                ):
                    st.error(f"You are not allowed to modify {table_name[0]} table!")
                    continue
            try:
                df = duckdb_conn.execute(str(statement)).df()
                insert_database_size()
                st.dataframe(df, hide_index=True, height=200, use_container_width=True)
            except (InternalException, FatalException):
                st.error("There is a fatal error in duckdb, the below SQL cannot be executed!")
                st.code(statement)
                duckdb_conn.close()
                get_duckdb_conn.clear()
            except Exception as error:
                st.error(error)

        st.session_state.sql_code = format_sql(sql_query)
        st.session_state.table_options = get_tables()


def display_duckdb_catalog():
    st.subheader("Data Catalogue", anchor=False)
    search = st.text_input("Search for a table or column")
    duckdb_conn = get_duckdb_conn()
    if not search:
        for table in st.session_state.table_options:
            with st.expander(table):
                for col in duckdb_conn.execute(
                    f"select column_name from duckdb_columns where table_name = '{table}' order by column_name"
                ).fetchall():
                    st.markdown(f"- {col[0]}")
    else:
        for table in duckdb_conn.execute(
            f"""
            select distinct table_name
                from duckdb_columns
            where column_name ilike '%{search}%' or table_name ilike '%{search}%'
            order by table_name
        """
        ).fetchall():
            with st.expander(table[0]):
                for col in duckdb_conn.execute(
                    f"select column_name from duckdb_columns where table_name = '{table[0]}' order by column_name"
                ).fetchall():
                    st.markdown(f"- {col[0]}")


def get_code_editor():

    header_col, _, download_col = st.columns([1, 1, 1])

    with header_col:
        st.subheader("Editor", anchor=False)

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
        # completions=[{"caption": table, "value": table} for table in st.session_state.table_options],
        allow_reset=True,
        key="sql-editor",
    )

    execute_sql(sql_editor)

    if st.session_state.sql_code:
        download_col.download_button(
            "Download code",
            data=st.session_state.sql_code,
            file_name=f"own_your_data_code_{datetime.datetime.now().isoformat()}.sql",
            help="Download the code written in the editor",
            use_container_width=True,
            icon="⬇️",
        )
