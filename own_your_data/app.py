import os
import shutil
import uuid
from pathlib import Path

import streamlit as st
from components.python_editor import get_py_code_editor

from own_your_data.components.chart_configuration import get_cached_plot
from own_your_data.components.chart_configuration import get_chart_configuration
from own_your_data.components.chart_configuration import get_chart_layout
from own_your_data.components.chart_configuration import get_charts_components
from own_your_data.components.data_analysis import get_data_analysis_components
from own_your_data.components.import_file import copy_imported_database
from own_your_data.components.import_file import get_table_name
from own_your_data.components.import_file import get_unzipped_data
from own_your_data.components.import_file import import_demo_file
from own_your_data.components.import_file import import_uploaded_file
from own_your_data.components.import_file import process_imported_data
from own_your_data.components.sql_editor import display_duckdb_catalog
from own_your_data.components.sql_editor import get_code_editor
from own_your_data.components.system_info import get_system_info
from own_your_data.utils import add_timestamp_to_str
from own_your_data.utils import cache_duckdb_execution
from own_your_data.utils import cleanup_db
from own_your_data.utils import export_database_and_zip
from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import get_tables
from own_your_data.utils import initial_load

st.set_page_config(layout="wide", page_title="Own Your Data Playground")

Path(f"{str(Path.home())}/own-your-data").mkdir(exist_ok=True)
Path(f"{str(Path.home())}/own-your-data/imports").mkdir(exist_ok=True)

st.markdown(
    """
        <h1>
            Own Your Data
            <p style="display:inline;font-size:18px">
                on your machine, in your browser
            </p>
        </h1>
    """,
    unsafe_allow_html=True,
)
st.divider()
get_duckdb_conn()

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4()
    st.session_state.logging = ""
    initial_load()
    import_demo_file()


if "table_options" not in st.session_state:
    st.session_state.table_options = get_tables()
    st.session_state.index_option = st.session_state.table_options.index("file_demo_file_txt_t")

if "sql_code" not in st.session_state:
    st.session_state.sql_code = None

if "py_code" not in st.session_state:
    st.session_state.py_code = None

if "import_type" not in st.session_state:
    st.session_state.import_type = "overwrite"

about_col, import_data_col, export_data_col, _ = st.columns([1, 1, 1, 1], gap="small", vertical_alignment="center")

with about_col.popover("How To", use_container_width=True, icon="ℹ️"):
    # pre-commit is removing trailing whitespace, which is not desired in this text
    st.markdown(
        f"""➜Import your data by pressing the :green[**Import Data**] button{"  "}
        ➜Configure your charts in the :green[**Visualize Data**] section{"  "}
        ➜Analyze your data with SQL in the :green[**SQL Editor**] section{"  "}
        ➜Analyze your data with Python in the :green[**Python Editor**] section{"  "}
        ➜Check out the system information in the :green[**System Information**] section{"  "}
        The source code of this application is available on [github](https://github.com/acirtep/own-your-data)
        """
    )

with import_data_col.popover("Import Data", use_container_width=True, icon="⬆️"):
    with st.form("import data", clear_on_submit=True):
        import_type = st.radio(
            "How to handle objects with the same name?",
            ["overwrite", "rename"],
            index=["overwrite", "rename"].index(st.session_state.import_type),
            captions=[
                "Replace them with the imported data",
                "Rename the imported ones by adding a timestamp and possible duplicate data",
            ],
        )
        st.session_state.import_type = import_type
        data_source = st.file_uploader(
            "Choose a file",
            type=["csv", "txt", "zip", "tsv", "duckdb"],
            help="""
            Upload a file in csv or txt format in which you have data you would like to explore. \n
            You can also upload a zip of csv/txt files, they should contain similar data as they will be
            imported in the same table. \n
            A demo file is available at
             [github](https://github.com/acirtep/own-your-data/blob/main/own_your_data/demo/demo_file.txt)
        """,
        )
        add_auto_columns = st.checkbox("Automatically parse date fields into year, month name and day name", value=True)
        submitted = st.form_submit_button("Upload file")
        st.warning("When the import is done a success message is displayed")

    if submitted and data_source:
        table_name = get_table_name(data_source.name)
        final_table_name = f"{table_name}_t"
        import_error = False

        if st.session_state.import_type == "overwrite":
            cleanup_db(final_table_name)
        else:
            table_name = add_timestamp_to_str(final_table_name)

        try:
            imported_file_path = f"{str(Path.home())}/own-your-data/imports/{data_source.name}"
            imported_file_name = data_source.name.lower()

            with open(imported_file_path, "wb") as imported_file:
                imported_file.write(data_source.getvalue())

            match data_source.type:
                case "application/zip":
                    csv_txt_files = get_unzipped_data(imported_file_path, file_types=[".csv", ".txt"])
                    duckdb_file = get_unzipped_data(imported_file_path, file_types=[".duckdb"])

                    if csv_txt_files:
                        import_uploaded_file(
                            data_source=get_unzipped_data(imported_file_path, file_types=[".csv", ".txt"]),
                            table_name=table_name,
                            file_name=data_source.name,
                        )
                        process_imported_data(table_name=table_name, add_auto_columns=add_auto_columns)

                    if duckdb_file:
                        final_table_name = None
                        copy_imported_database(duckdb_file[0], data_source.name)

                    shutil.rmtree(f"{str(Path.home())}/own-your-data/imports/unzipped")

                case "application/octet-stream":

                    final_table_name = None
                    copy_imported_database(imported_file_path, data_source.name)

                case _:
                    import_uploaded_file(
                        data_source=imported_file_path,
                        table_name=table_name,
                        file_name=data_source.name,
                    )
                    process_imported_data(table_name=table_name, add_auto_columns=add_auto_columns)
        except Exception as err:
            st.error(f"There was an error importing the data {err}")
            import_error = True
        finally:
            os.remove(imported_file_path)
            st.session_state.table_options = get_tables()
            st.session_state.index_option = (
                st.session_state.table_options.index(final_table_name) if final_table_name else 0
            )
            get_cached_plot.clear()
            cache_duckdb_execution.clear()

            if not import_error:
                if final_table_name:
                    st.success(f"File {data_source.name} successfully imported into {final_table_name} table")
                else:
                    st.success(f"Successfully imported {data_source.name}")

with export_data_col.popover("Export Data", use_container_width=True, icon="⬇️"):
    download_options = st.radio(
        "How do you want to download the data?",
        options=["DuckDB format", "SQL and CSV"],
        captions=[
            "Download as .duckdb file, can be used to open/attach in a DuckDB session. It can be imported back in :green[**Import Data**]",  # NOQA
            "Download in a directory, as a result of DuckDB export. This might take a while.",
        ],
    )

    match download_options:
        case "DuckDB format":
            with open(f"{str(Path.home())}/own-your-data/own_your_data.duckdb", "rb") as db:
                st.download_button(
                    "Export",
                    data=db,
                    file_name=f"{add_timestamp_to_str('own_your_data')}.duckdb",
                )
        case "SQL and CSV":
            with open(export_database_and_zip(), "rb") as zipped_directory:
                st.download_button(
                    "Export",
                    data=zipped_directory,
                    file_name=f"{add_timestamp_to_str('own_your_data')}.zip",
                )
        case _:
            st.error("Not implemented")

chart_tab, sql_editor_tab, python_editor_tab, system_info_tab = st.tabs(
    ["Visualize Data", "SQL Editor", "Python Editor", "System Information"]
)

with sql_editor_tab:
    with st.container():
        duckdb_catalog_col, sql_editor_col = st.columns([1, 3])
        with sql_editor_col:
            get_code_editor()
        with duckdb_catalog_col:
            with st.container(height=500):
                display_duckdb_catalog()


with python_editor_tab:
    get_py_code_editor()


with chart_tab:
    chart_config_col, chart_col = st.columns([1, 3])

    with chart_config_col:
        with st.container(border=True):
            selected_table = st.selectbox(
                "Select a table",
                options=st.session_state.table_options,
                index=st.session_state.index_option,
                help="The uploaded files are saved in tables prefixed with `file_`",
            )

            if selected_table:
                chart_configuration = get_chart_configuration(table_name=selected_table)

                with chart_col:
                    get_data_analysis_components(table_name=selected_table)
                    if chart_configuration:
                        chart_configuration = get_chart_layout(chart_configuration)
                        try:
                            get_charts_components(chart_configuration=chart_configuration)
                        except Exception as error:  # NOQA everything can go wrong
                            st.error(f"Something went wrong: {error}")
                    else:
                        st.warning("Visualize the data as a chart by configuring it on the left side")

with system_info_tab:
    get_system_info()
