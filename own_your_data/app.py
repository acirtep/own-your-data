import streamlit as st

from own_your_data.components.charts import get_charts_components
from own_your_data.components.data_analysis import get_data_analysis_components
from own_your_data.components.import_file import cleanup_db
from own_your_data.components.import_file import import_uploaded_file
from own_your_data.components.import_file import process_file
from own_your_data.components.sidebar import get_sidebar_chart_configuration
from own_your_data.utils import get_duckdb_conn


def main():
    st.set_page_config(layout="wide")
    st.title(
        "Own Your Data \n on your machine, in your browser [🔎source code](https://github.com/acirtep/own-your-data)",
        anchor=False,
    )

    if "data_imported" not in st.session_state:
        st.session_state.data_imported = False

    get_duckdb_conn()

    with st.sidebar.expander("Import data"):
        data_source = st.file_uploader("Upload file", type=["csv", "txt"])

    if data_source:
        st.session_state.data_imported = True
        try:
            st.header(f"Data analysis of {data_source.name}", anchor=False)
            cleanup_db(file_id=data_source.file_id)
            import_uploaded_file(data_source=data_source, file_id=data_source.file_id)
            process_file(file_id=data_source.file_id)
            get_data_analysis_components(file_id=data_source.file_id)
            sidebar_chart_configuration = get_sidebar_chart_configuration(file_id=data_source.file_id)
            if not sidebar_chart_configuration:
                st.error("Please configure the chart in the sidebar area!")
            else:
                get_charts_components(chart_configuration=sidebar_chart_configuration)
        except Exception as error:  # NOQA everything can go wrong
            st.error(f"Something went wrong {error}")

    if not st.session_state.data_imported:
        st.warning("Start analysing data by importing it in the sidebar")


if __name__ == "__main__":
    main()
