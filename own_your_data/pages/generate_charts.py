import streamlit
import streamlit as st

from own_your_data.charts.charts import BarChart
from own_your_data.charts.charts import HeatMapChart
from own_your_data.charts.charts import LineChart
from own_your_data.charts.charts import SankeyChart
from own_your_data.charts.constants import DEFAULT_METRIC_COLUMN
from own_your_data.charts.constants import SupportedPlots
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

    plot_type = st.sidebar.radio("✅ plot type", SupportedPlots.list(), horizontal=True)

    title = st.sidebar.text_input(label="✅ plot title", max_chars=100, value="Title")

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

            with st.expander("Preview data (max 3000)", expanded=True):
                st.dataframe(duckdb_conn.execute("select * from csv_import_t limit 3000").df(), hide_index=True)

            with st.expander("Data summary", expanded=True):
                st.dataframe(duckdb_conn.execute("select * from csv_import_summary_t limit 3000").df())

            st.header("Data visualization", anchor=False, divider=True)

            match plot_type:
                case SupportedPlots.bar:
                    dim_column = st.sidebar.selectbox("Select the dimension", columns, index=0)
                    color_column = st.sidebar.selectbox("Select a color dimension", columns, index=0)
                    orientation = st.sidebar.radio(
                        "✅ orientation",
                        ("h", "v"),
                        help="h=horizontal, v=vertical, default h",
                        horizontal=True,
                        index=1,
                    )
                    bar_chart = BarChart(
                        duckdb_conn=duckdb_conn,
                        metric_column=metric_column,
                        dim_columns=[dim_column],
                        color_column=color_column,
                        orientation=orientation,
                    )
                    fig_plot = bar_chart.plot
                    sql_query = bar_chart.sql_query

                case SupportedPlots.sankey:
                    flow_columns = st.sidebar.multiselect(
                        "Select the category columns",
                        columns,
                        help="Add which columns to appear in the plot in the desired order",
                    )
                    sankey_chart = SankeyChart(
                        duckdb_conn=duckdb_conn,
                        metric_column=metric_column,
                        dim_columns=flow_columns,
                        color_column=None,
                        orientation=None,
                    )
                    fig_plot = sankey_chart.plot
                    fig_plot.update_traces(arrangement="snap", selector=dict(type="sankey"))
                    sql_query = sankey_chart.sql_query

                case SupportedPlots.line:
                    dim_column = st.sidebar.selectbox("Select the dimension", columns, index=0)
                    color_column = st.sidebar.selectbox("Select a color dimension", columns, index=0)
                    line_chart = LineChart(
                        duckdb_conn=duckdb_conn,
                        metric_column=metric_column,
                        dim_columns=[dim_column],
                        color_column=color_column,
                        orientation=None,
                    )
                    fig_plot = line_chart.plot
                    sql_query = line_chart.sql_query

                case SupportedPlots.heatmap:
                    x_column = st.sidebar.selectbox("Select X-axis dimension", columns, index=0)
                    y_column = st.sidebar.selectbox("Select Y-axis dimension", columns, index=1)
                    heatmap_chart = HeatMapChart(
                        duckdb_conn=duckdb_conn,
                        metric_column=metric_column,
                        dim_columns=[x_column],
                        color_column=y_column,
                        orientation=None,
                    )
                    fig_plot = heatmap_chart.plot
                    sql_query = heatmap_chart.sql_query

                case _:
                    fig_plot = None
                    sql_query = None

            if fig_plot:
                fig_plot.update_layout(title=title, height=height, width=width, font_size=14, font_color="black")
                with st.expander("SQL query"):
                    st.code(sql_query)
                st.plotly_chart(fig_plot, use_container_width=False)

        except Exception as error:
            st.error(f":red[Something went wrong] {error}")  # NOQA
