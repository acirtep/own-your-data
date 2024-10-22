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
from own_your_data.components.system_info import get_system_info
from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import get_tables
from own_your_data.utils import initial_load

st.set_page_config(layout="wide", page_title="Own Your Data Playground")

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
    initial_load()
    import_demo_file()


if "table_options" not in st.session_state:
    st.session_state.table_options = get_tables()
    st.session_state.index_option = st.session_state.table_options.index("file_demo_file_txt_t")

if "sql_code" not in st.session_state:
    st.session_state.sql_code = None

about_col, import_data_col, _, _ = st.columns([1, 1, 1, 1], gap="small", vertical_alignment="center")

with about_col.popover("How To", use_container_width=True, icon="ℹ️"):
    # pre-commit is removing trailing whitespace, which is not desired in this text
    st.markdown(
        f"""➜Import your data by pressing the :green[**Import Data**] button{"  "}
        ➜Configure your charts in the :green[**Visualize Data**] section{"  "}
        ➜Analyze your data with SQL in the :green[**SQL Editor**] section{"  "}
        ➜Check out the system information in the :green[**System Information**] section{"  "}
        The source code of this application is available on [github](https://github.com/acirtep/own-your-data)
        """
    )

with import_data_col.popover("Import Data", use_container_width=True, icon="⬆️"):
    with st.form("import data", clear_on_submit=True):
        st.warning("Uploading a file with the same name will result into overwriting the data.")
        data_source = st.file_uploader(
            "Choose a file",
            type=["csv", "txt", "zip"],
            help="""
            Upload a file in csv or txt format in which you have data you would like to explore. \n
            You can also upload a zip of csv/txt files, they should contain similar data as they will be
            imported in the same table. \n
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
        except Exception as error:  # NOQA everything can go wrong
            st.error(f"Something went wrong {error}")

# with export_data_col.popover("Export from database"):
#     st.info("In order to export specific tables, go to `SQL Editor`, do a `select * from` and download the result.\
#             The functionality to export a selection of tables is under development.")
#     with open(f"{Path(__file__).parent}/own_your_data.db", "rb") as db:
#         duckdb_conn = get_duckdb_conn()
#         duckdb_conn.close()
#         get_duckdb_conn.clear()
#         st.download_button(
#             "Export entire database",
#             data=db,
#             file_name=f"own_your_data_{datetime.datetime.now().isoformat()}.db",
#             help="Export the database in duckdb format",
#         )

chart_tab, sql_editor_tab, system_info_tab = st.tabs(["Visualize Data", "SQL Editor", "System Information"])

with sql_editor_tab:
    with st.container():
        duckdb_catalog_col, sql_editor_col = st.columns([1, 3])
        with sql_editor_col:
            get_code_editor()
        with duckdb_catalog_col:
            with st.container(height=500):
                display_duckdb_catalog()

with chart_tab:
    with st.container():
        chart_config_col, chart_col = st.columns([1, 3])
        with chart_config_col:
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
                try:
                    get_charts_components(chart_configuration=chart_configuration)
                except Exception as error:  # NOQA everything can go wrong
                    st.error(f"Something went wrong {error}")
            else:
                st.warning("Visualize the data as a chart by configuring it on the left side")

with system_info_tab:
    get_system_info()
