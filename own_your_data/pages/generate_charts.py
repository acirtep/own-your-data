import streamlit as st

from own_your_data.charts.charts import BarChart
from own_your_data.charts.charts import LineChart
from own_your_data.charts.charts import SankeyChart
from own_your_data.charts.constants import DEFAULT_METRIC_COLUMN
from own_your_data.charts.import_file import cleanup_db
from own_your_data.charts.import_file import import_csv_and_process_data
from own_your_data.utils import get_duckdb_conn

st.set_page_config(layout="wide")


if __name__ == "__main__":

    duckdb_conn = get_duckdb_conn()

    with st.sidebar.expander("Data source"):
        cleanup_db(duckdb_conn=duckdb_conn)
        data_source = st.sidebar.file_uploader("✅ upload file(s)", type=["csv", "txt"])

    height = st.sidebar.slider("✅ height", min_value=400, max_value=4000, step=50)

    width = st.sidebar.slider("✅ width", min_value=600, max_value=3000, step=50, value=1200)

    orientation = st.sidebar.radio(
        "✅ orientation", ("h", "v"), help="h=horizontal, v=vertical, default h", horizontal=True
    )

    plot_type = st.sidebar.radio("✅ plot type", ("bar", "sankey", "line"), horizontal=True)

    title = st.sidebar.text_input(label="✅ plot title", max_chars=100)

    if data_source:
        import_csv_and_process_data(data_source=data_source)
        columns = [
            column[0]
            for column in duckdb_conn.execute(
                "select column_name from csv_import_summary_t order by column_name"
            ).fetchall()
        ]

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
                    fig_plot = bar_chart.plot
                    sql_query = bar_chart.sql_query

                case "sankey":
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
                    fig_plot = sankey_chart.plot
                    fig_plot.update_traces(arrangement="snap", selector=dict(type="sankey"))
                    sql_query = sankey_chart.sql_query

                case "line":
                    dim_column = st.sidebar.selectbox("Select the dimension", dimension_columns, index=0)
                    color_column = st.sidebar.selectbox("Select a color dimension", dimension_columns, index=0)
                    line_chart = LineChart(
                        duckdb_conn=duckdb_conn,
                        metric_column=metric_column,
                        dim_columns=[dim_column],
                        color_column=color_column,
                        orientation=orientation,
                    )
                    fig_plot = line_chart.plot
                    sql_query = line_chart.sql_query

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
