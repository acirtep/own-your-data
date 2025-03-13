import streamlit as st
from code_editor import code_editor
from utils import add_timestamp_to_str
from utils import cache_duckdb_execution
from utils import get_tables


def get_py_code_editor():

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
    py_editor = code_editor(
        code="""
# get duckdb connection
# from own_your_data.utils import get_duckdb_conn
# duckdb_conn = get_duckdb_conn()
""",
        lang="python",
        buttons=execution_buttons,
        allow_reset=True,
        key="python-editor",
    )

    if py_editor.get("type") == "submit":
        py_code = py_editor.get("text")
        st.session_state.py_code = py_code
        try:
            exec(py_code, globals(), globals())
            cache_duckdb_execution.clear()
            st.session_state.table_options = get_tables()
            st.session_state.index_option = None
        except Exception as e:
            st.exception(e)

    if st.session_state.py_code:
        download_col.download_button(
            "Download code",
            data=st.session_state.py_code,
            file_name=f"{add_timestamp_to_str('own_your_data_code')}.py",
            help="Download the code written in the editor",
            use_container_width=True,
            icon="⬇️",
        )
