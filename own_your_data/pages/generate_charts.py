import re

import duckdb
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from own_your_data.charts import BarChart
from own_your_data.charts import SankeyChart
from own_your_data.constants import DEFAULT_METRIC_COLUMN

st.set_page_config(layout="wide")


@st.cache_resource
def get_duckdb_conn_with_data(data_source: UploadedFile) -> (duckdb.DuckDBPyConnection, list[str]):
    duckdb_conn = duckdb.connect()
    columns = []
    try:
        imported_data = duckdb_conn.read_csv(data_source)
        duckdb_conn.execute("create table csv_import as select * from imported_data")
        for column in imported_data.columns:
            new_column_name = " ".join(re.sub("[^A-Za-z0-9 ]+", " ", column).title().split())
            columns.append(new_column_name)
            duckdb_conn.execute(f'alter table csv_import rename "{column}" to "{new_column_name}"')

        duckdb_conn.execute("create table csv_import_summary as SELECT * FROM (SUMMARIZE csv_import)")
    except Exception as error:
        st.error(f":red[Something went wrong] {error}")  # NOQA
        raise error

    date_related_columns = duckdb_conn.execute(
        """
        select column_name
        from csv_import_summary
        where column_type = 'DATE' or column_type like 'TIMESTAMP%'
        """
    ).fetchall()

    date_related_expressions = ""
    for date_related_column in date_related_columns:
        new_month_column = f"{date_related_column[0]} Month Name"
        new_day_column = f"{date_related_column[0]} Day Name"
        date_related_expressions = f"""
            monthname("{date_related_column[0]}") as "{new_month_column}",
            dayname("{date_related_column[0]}") as "{new_day_column}",
            {date_related_expressions}
        """
        columns.append(new_month_column)
        columns.append(new_day_column)

    duckdb_conn.execute(
        f"""
        create table csv_import_t as
        select it.*, {date_related_expressions}
        from csv_import it
    """
    )
    duckdb_conn.execute("drop table csv_import")
    duckdb_conn.execute("drop table csv_import_summary")
    duckdb_conn.execute("create table csv_import_summary_t as SELECT * FROM (SUMMARIZE csv_import_t)")

    return duckdb_conn, columns


def preview_data_and_get_plot(data_source: UploadedFile, plot_type: str):
    duckdb_conn, columns = get_duckdb_conn_with_data(data_source)

    try:
        numeric_columns = [
            column[0]
            for column in duckdb_conn.execute(
                """
            select column_name
            from csv_import_summary_t
            order by case when column_type in ('DOUBLE', 'FLOAT', 'INTEGER')
                or column_type like '%INT' then 0 else 1 end, column_name
            """
            ).fetchall()
        ]
        numeric_columns.append(DEFAULT_METRIC_COLUMN)

        metric_column = st.sidebar.selectbox("Select the metric", numeric_columns)
        dimension_columns = tuple(set(columns) - set([metric_column]))

        with st.expander("Preview data (max 3000)", expanded=True):
            st.dataframe(duckdb_conn.execute("select * from csv_import_t limit 3000").df(), hide_index=True)

        with st.expander("Data summary", expanded=True):
            st.dataframe(duckdb_conn.execute("select * from csv_import_summary_t limit 3000").df())

        st.header("Data visualization", anchor=False, divider=True)

        match plot_type:
            case "bar":
                dim_column = st.sidebar.selectbox("Select the dimension", dimension_columns, index=0)
                color_column = st.sidebar.selectbox("Select a color dimension", dimension_columns, index=0)
                bar_chart = BarChart(
                    duckdb_conn=duckdb_conn,
                    metric_column=metric_column,
                    dim_columns=[dim_column],
                    color_column=color_column,
                    orientation=orientation,
                )
                fig_plot = bar_chart.get_plot()
                sql_query = bar_chart.sql_query

            case "sankey":
                arrangement = st.sidebar.radio(
                    "✅ arrangement",
                    ("snap", "perpendicular", "freeform", "fixed"),
                    help="""Default: "snap"
                    If value is `snap` (the default), the node arrangement is assisted by automatic snapping of \
                    elements to preserve space between nodes specified via `nodepad`. If value is `perpendicular`,\
                    the nodes can only move along a line perpendicular to the flow. If value is `freeform`, \
                    the nodes can freely move on the plane. If value is `fixed`, the nodes are stationary.""",
                    horizontal=True,
                )

                flow_columns = st.sidebar.multiselect(
                    "Select the category columns",
                    dimension_columns,
                    help="Add which columns to appear in the plot in the desired order",
                )
                sankey_chart = SankeyChart(
                    duckdb_conn=duckdb_conn,
                    metric_column=metric_column,
                    dim_columns=flow_columns,
                    color_column=None,
                    orientation=orientation,
                )
                fig_plot = sankey_chart.get_plot()
                fig_plot.update_traces(arrangement=arrangement, selector=dict(type="sankey"))
                sql_query = sankey_chart.sql_query

            case _:
                fig_plot = None
                sql_query = None

        if fig_plot:
            fig_plot.update_layout(
                title=title,
                height=height,
                width=width,
            )
            with st.expander("SQL query"):
                st.code(sql_query)
            st.plotly_chart(fig_plot, use_container_width=False)

    except Exception as error:
        st.error(f":red[Something went wrong] {error}")  # NOQA


with st.spinner("Importing data in memory..."):

    with st.sidebar.expander("Data source"):
        data_source = st.sidebar.file_uploader("✅ upload file(s)", type=["csv", "txt"])

    height = st.sidebar.slider("✅ height", min_value=400, max_value=4000, step=50)

    width = st.sidebar.slider("✅ width", min_value=600, max_value=3000, step=50, value=1200)

    orientation = st.sidebar.radio(
        "✅ orientation", ("h", "v"), help="h=horizontal, v=vertical, default h", horizontal=True
    )

    plot_type = st.sidebar.radio("✅ plot type", ("bar", "sankey"), horizontal=True)

    title = st.sidebar.text_input(label="✅ plot title", max_chars=100)

    if data_source:
        preview_data_and_get_plot(data_source=data_source, plot_type=plot_type)
