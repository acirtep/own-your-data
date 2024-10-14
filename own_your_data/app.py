import uuid

import streamlit as st

from own_your_data.components.charts import get_charts_components
from own_your_data.components.data_analysis import get_code_editor
from own_your_data.components.data_analysis import get_data_analysis_components
from own_your_data.components.import_file import cleanup_db
from own_your_data.components.import_file import get_table_name
from own_your_data.components.import_file import import_demo_file
from own_your_data.components.import_file import import_uploaded_file
from own_your_data.components.import_file import process_imported_data
from own_your_data.components.sidebar import get_sidebar_chart_configuration
from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import get_tables


def get_components_for_table(table_name):
    try:
        sidebar_chart_configuration = get_sidebar_chart_configuration(table_name=table_name)
        if not sidebar_chart_configuration:
            pass
        else:
            get_charts_components(chart_configuration=sidebar_chart_configuration)
    except Exception as error:  # NOQA everything can go wrong
        st.error(f"Something went wrong {error}")


def main():
    st.set_page_config(layout="wide", page_title="Own Your Data Playground")
    st.title(
        "Own Your Data \n on your machine, in your browser [🔎source code](https://github.com/acirtep/own-your-data)",
        anchor=False,
    )

    get_duckdb_conn()

    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4()

    import_demo_file(session_id=st.session_state.session_id)

    if "table_options" not in st.session_state:
        st.session_state.table_options = get_tables()
        st.session_state.index_option = 0

    with st.sidebar.expander("Import data"):
        data_source = st.file_uploader("Upload a file", type=["csv", "txt"])
        st.info(
            "A demo file is available at \
             [github](https://github.com/acirtep/own-your-data/blob/main/own_your_data/demo/demo_file.txt)"
        )

    if data_source:

        table_name = get_table_name(data_source.name)
        final_table_name = f"{table_name}_t"
        try:
            cleanup_db(table_name=final_table_name)
            import_uploaded_file(data_source=data_source, table_name=table_name, file_id=data_source.file_id)
            process_imported_data(table_name=table_name, file_id=data_source.file_id)
            st.success(f"File {data_source.name} successfully imported into {final_table_name} table")
            st.session_state.table_options = get_tables()
            st.session_state.index_option = st.session_state.table_options.index(final_table_name)
        except Exception as error:  # NOQA everything can go wrong
            st.error(f"Something went wrong {error}")

    selected_table = st.sidebar.selectbox(
        "Pick a table",
        options=st.session_state.table_options,
        index=st.session_state.index_option,
        disabled=data_source is not None,
    )

    data_tab, code_tab = st.tabs(["Data Visualization", "SQL editor"])
    with code_tab:
        get_code_editor()

    with data_tab:
        if selected_table:
            st.subheader(f"Data analysis of {selected_table} table")
            get_data_analysis_components(table_name=selected_table)
            get_components_for_table(table_name=selected_table)


if __name__ == "__main__":
    main()
