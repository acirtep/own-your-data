import streamlit as st

from own_your_data.charts.charts import BarChart
from own_your_data.charts.charts import HeatMapChart
from own_your_data.charts.charts import LineChart
from own_your_data.charts.charts import SankeyChart
from own_your_data.charts.constants import SupportedAggregationMethods
from own_your_data.charts.constants import SupportedPlots
from own_your_data.charts.import_file import cleanup_db
from own_your_data.charts.import_file import import_csv_and_process_data
from own_your_data.utils import custom_sidebar
from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import init_session

custom_sidebar()
init_session()


duckdb_conn = get_duckdb_conn()


with st.expander("Import data", expanded=True):
    cleanup_db(duckdb_conn=duckdb_conn)
    data_source = st.file_uploader("Upload file", type=["csv", "txt"])

if data_source:
    st.header(f"Data analysis of {data_source.name}", anchor=False)
    import_csv_and_process_data(data_source=data_source)

    columns = [
        column[0]
        for column in duckdb_conn.execute(
            "select column_name from csv_import_summary_t order by column_name"
        ).fetchall()
    ]
    if len(columns) < 2:
        st.error("There needs to be at least 2 columns in the file!")
    else:

        data_preview, data_summary = st.columns(2)

        with data_preview:
            with st.expander("Preview data (max 3000)"):
                st.dataframe(
                    duckdb_conn.execute("select * from csv_import_t limit 3000").df(), hide_index=True, height=200
                )

        with data_summary:
            with st.expander("Data summary"):
                st.dataframe(
                    duckdb_conn.execute("select * from csv_import_summary_t limit 3000").df(),
                    hide_index=True,
                    height=200,
                )

        st.header("Visualize data", anchor=False)
        plot_config, plot_display = st.columns([1, 3], vertical_alignment="center")

        with plot_config:

            height = st.slider("Height", min_value=400, max_value=4000, step=50)

            width = st.slider("Width", min_value=600, max_value=3000, step=50, value=1200)

            title = st.text_input(label="Title", max_chars=100, value="Title")

            plot_type = st.radio("Type", SupportedPlots.list(), horizontal=True)

            aggregation_method = st.radio(
                "Select the aggregation method", SupportedAggregationMethods.list(), horizontal=True, index=1
            )

            numeric_columns = [
                column[0]
                for column in duckdb_conn.execute(
                    """
                select column_name
                from csv_import_summary_t
                order by case when column_type in ('DOUBLE', 'FLOAT', 'INTEGER') then 0
                    when column_type like '%INT' then 1 else 2 end, column_name
                """
                ).fetchall()
            ]

            metric_column = st.selectbox("Select the metric", numeric_columns)

        match plot_type:
            case SupportedPlots.bar:
                dim_column = plot_config.selectbox("Select the dimension", columns, index=0)
                color_column = plot_config.selectbox("Select a color dimension", columns, index=0)
                orientation = plot_config.radio(
                    "Orientation",
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
                    aggregation_method=aggregation_method,
                )
                fig_plot = bar_chart.plot
                sql_query = bar_chart.sql_query

            case SupportedPlots.sankey:
                flow_columns = plot_config.multiselect(
                    "Select the category columns",
                    columns,
                    help="Add which columns to appear in the plot in the desired order",
                )

                if len(flow_columns) < 2:
                    plot_display.error("There need to be at least 2 columns selected!")
                    fig_plot = None
                    sql_query = None
                else:
                    sankey_chart = SankeyChart(
                        duckdb_conn=duckdb_conn,
                        metric_column=metric_column,
                        dim_columns=flow_columns,
                        color_column=None,
                        orientation=None,
                        aggregation_method=aggregation_method,
                    )
                    fig_plot = sankey_chart.plot
                    fig_plot.update_traces(arrangement="snap", selector=dict(type="sankey"))
                    sql_query = sankey_chart.sql_query

            case SupportedPlots.line:
                dim_column = plot_config.selectbox("Select the dimension", columns, index=0)
                color_column = plot_config.selectbox("Select a color dimension", columns, index=0)
                line_chart = LineChart(
                    duckdb_conn=duckdb_conn,
                    metric_column=metric_column,
                    dim_columns=[dim_column],
                    color_column=color_column,
                    orientation=None,
                    aggregation_method=aggregation_method,
                )
                fig_plot = line_chart.plot
                sql_query = line_chart.sql_query

            case SupportedPlots.heatmap:
                x_column = plot_config.selectbox("Select X-axis dimension", columns, index=0)
                y_column = plot_config.selectbox("Select Y-axis dimension", columns, index=1)
                heatmap_chart = HeatMapChart(
                    duckdb_conn=duckdb_conn,
                    metric_column=metric_column,
                    dim_columns=[x_column],
                    color_column=y_column,
                    orientation=None,
                    aggregation_method=aggregation_method,
                )
                fig_plot = heatmap_chart.plot
                sql_query = heatmap_chart.sql_query

            case _:
                fig_plot = None
                sql_query = None

        if fig_plot:
            fig_plot.update_layout(title=title, height=height, width=width, font_size=14, font_color="black")
            plot_display.plotly_chart(fig_plot, use_container_width=False)

            with st.expander("SQL query for plot"):
                st.code(sql_query)
