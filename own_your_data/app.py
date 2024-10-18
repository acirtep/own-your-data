import uuid

import streamlit as st

from own_your_data.components.chart_configuration import get_chart_configuration
from own_your_data.components.charts import get_charts_components
from own_your_data.components.data_analysis import get_data_analysis_components
from own_your_data.components.import_file import cleanup_db
from own_your_data.components.import_file import get_table_name
from own_your_data.components.import_file import get_unzipped_data
from own_your_data.components.import_file import import_demo_file
from own_your_data.components.import_file import import_uploaded_file
from own_your_data.components.import_file import process_imported_data
from own_your_data.components.sql_editor import display_duckdb_catalog
from own_your_data.components.sql_editor import get_code_editor
from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import get_tables


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

    import_data_tab, chart_tab, sql_editor_tab = st.tabs(["Import Data", "Visualize Data", "SQL Editor"])

    with import_data_tab:
        with st.form("import data", clear_on_submit=True):
            data_source = st.file_uploader(
                "Choose a file",
                type=["csv", "txt", "zip"],
                help="""
                Upload a file in csv or txt format in which you have data you would like to explore. \n
                You can also upload a zip of csv/txt files, they should contain similar data as they will be
                imported in the same table. \n
                Uploading a file multiple times will result into overwriting the data. \n
                A demo file is available at
                 [github](https://github.com/acirtep/own-your-data/blob/main/own_your_data/demo/demo_file.txt)
            """,
            )
            submitted = st.form_submit_button("Upload file")

        if submitted and data_source:
            table_name = get_table_name(data_source.name)
            final_table_name = f"{table_name}_t"
            try:
                cleanup_db(table_name=final_table_name)
                if data_source.type == "application/zip":
                    import_uploaded_file(
                        data_source=get_unzipped_data(data_source=data_source),
                        table_name=table_name,
                        file_name=data_source.name,
                    )
                else:
                    import_uploaded_file(
                        data_source=[data_source],
                        table_name=table_name,
                        file_name=data_source.name,
                    )
                process_imported_data(table_name=table_name)
                st.success(f"File {data_source.name} successfully imported into {final_table_name} table")
                st.session_state.table_options = get_tables()
                st.session_state.index_option = st.session_state.table_options.index(final_table_name)
                get_data_analysis_components(table_name=final_table_name)
            except Exception as error:  # NOQA everything can go wrong
                st.error(f"Something went wrong {error}")

    with sql_editor_tab:
        duckdb_catalog_col, sql_editor_col = st.columns([1, 3])
        with sql_editor_col:
            with st.container():
                get_code_editor()
        with duckdb_catalog_col:
            with st.container():
                display_duckdb_catalog()

    with chart_tab:
        chart_config_col, chart_col = st.columns([1, 3])
        with chart_config_col:
            selected_table = st.selectbox(
                "Pick a table", options=st.session_state.table_options, index=st.session_state.index_option
            )

            if selected_table:
                chart_configuration = get_chart_configuration(table_name=selected_table)

        with chart_col:
            get_data_analysis_components(table_name=selected_table)
            if chart_configuration:
                try:
                    get_charts_components(chart_configuration=chart_configuration)
                except Exception as error:  # NOQA everything can go wrong
                    st.error(f"Something went wrong {error}")
            else:
                st.warning("Visualize the data as a chart by configuring it on the left side")


if __name__ == "__main__":
    main()
