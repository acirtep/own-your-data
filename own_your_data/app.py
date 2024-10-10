import uuid
from io import BytesIO
from pathlib import Path

import streamlit as st

from own_your_data.components.charts import get_charts_components
from own_your_data.components.data_analysis import get_data_analysis_components
from own_your_data.components.import_file import cleanup_db
from own_your_data.components.import_file import import_uploaded_file
from own_your_data.components.import_file import process_file
from own_your_data.components.sidebar import get_sidebar_chart_configuration
from own_your_data.utils import get_duckdb_conn


def get_components(file_name, file_id, data):
    try:
        st.header(f"Data analysis of {file_name}", anchor=False)
        cleanup_db(file_id=file_id)
        import_uploaded_file(data_source=data, file_id=file_id)
        process_file(file_id=file_id)
        get_data_analysis_components(file_id=file_id)
        sidebar_chart_configuration = get_sidebar_chart_configuration(file_id=file_id)
        if not sidebar_chart_configuration:
            st.error("Please configure the chart in the sidebar area!")
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

    if "data_imported" not in st.session_state:
        st.session_state.data_imported = False

    with st.sidebar.expander("Import data"):
        data_source = st.file_uploader("Upload file", type=["csv", "txt"])
        st.info(
            "The demo file is available at \
             [github](https://github.com/acirtep/own-your-data/blob/main/own_your_data/demo/demo_file.txt)"
        )
    if data_source:
        st.session_state.data_imported = True
        get_components(file_name=data_source.name, file_id=data_source.file_id, data=data_source)
        st.session_state.data_imported = True

    if not st.session_state.data_imported:
        st.warning(
            "The below data is based on demo data, you can play with it in the sidebar or \
        start analysing your data by importing it in the sidebar"
        )
        with open(f"{Path(__file__).parent}/demo/demo_file.txt") as demo_file:
            demo_data = BytesIO(demo_file.read().encode())
            get_components(file_name="demo_file.csv", file_id=uuid.uuid4(), data=demo_data)


if __name__ == "__main__":
    main()
