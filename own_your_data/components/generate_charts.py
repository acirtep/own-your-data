import streamlit as st

from own_your_data.charts.constants import SupportedAggregationMethods
from own_your_data.charts.constants import SupportedPlots
from own_your_data.charts.helpers import get_order_clause
from own_your_data.charts.import_file import cleanup_db
from own_your_data.charts.import_file import import_csv_and_process_data
from own_your_data.components.helpers import get_cached_plot
from own_your_data.utils import get_duckdb_conn


def main():

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

                    unique_values_query = " union all ".join(
                        [
                            f"""select '{column}' as column_name,
                                array_agg(distinct "{column}" order by {get_order_clause(column)}) as unique_value
                                from csv_import_t
                            """
                            for column in columns
                        ]
                    )

                    st.dataframe(
                        duckdb_conn.execute(
                            f"""
                        with unique_values_cte as (
                            {unique_values_query}
                        )
                            select t.* , string_agg(uvc.unique_value[:50], ',') as first_50_unique_values
                            from csv_import_summary_t t
                                left join unique_values_cte uvc on t.column_name = uvc.column_name
                            group by all
                        """
                        ).df(),
                        hide_index=True,
                        height=200,
                    )

            st.header("Visualize data", anchor=False)
            plot_config, plot_layout, _, plot_display = st.columns([0.5, 0.4, 0.1, 3], vertical_alignment="center")

            with plot_layout:

                height = st.slider("Height", min_value=400, max_value=4000, step=50, value=400)

                width = st.slider("Width", min_value=600, max_value=3000, step=50, value=900)

                title = plot_layout.text_input("Title", value="Title")
                x_label = plot_layout.text_input("X-axis label")
                y_label = plot_layout.text_input("Y-axis label")

            with plot_config:

                plot_type = st.radio("Type", SupportedPlots.list(), horizontal=True)

                aggregation_method = st.radio(
                    "Calculation", SupportedAggregationMethods.list(), horizontal=True, index=1
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

            requirements_met = False
            dim_columns = None
            match plot_type:
                case SupportedPlots.bar:
                    metric_column = plot_config.selectbox(
                        "Measurement column", numeric_columns, help="Displayed on Y-axis", index=None
                    )
                    x_column = plot_config.selectbox("X-axis", columns, index=None)

                    color_column = plot_config.selectbox(
                        "Color column", columns, help="A column to split the values with colors", index=None
                    )

                    orientation = plot_layout.radio(
                        "Orientation",
                        ("h", "v"),
                        help="h=horizontal, v=vertical, default h",
                        horizontal=True,
                        index=1,
                    )

                    if all([metric_column, x_column, color_column]):
                        dim_columns = [x_column]
                        requirements_met = True

                case SupportedPlots.sankey:
                    metric_column = plot_config.selectbox("Measurement column", numeric_columns, index=None)
                    flow_columns = plot_config.multiselect(
                        "Flow columns",
                        columns,
                        help="Add which columns to appear in the plot in the desired order",
                    )
                    color_column = None
                    orientation = None

                    if len(flow_columns) < 2:
                        plot_display.error("There need to be at least 2 columns selected!")
                        dim_columns = None
                        requirements_met = False
                    else:
                        if all([metric_column, flow_columns]):
                            dim_columns = flow_columns
                            requirements_met = True

                case SupportedPlots.line:
                    metric_column = plot_config.selectbox(
                        "Measurement column", numeric_columns, help="Displayed on Y-axis", index=None
                    )
                    x_column = plot_config.selectbox("Select X-axis dimension", columns, index=None)
                    color_column = plot_config.selectbox(
                        "Color column", columns, index=None, help="A column to split the values with colors"
                    )
                    orientation = None

                    if all([metric_column, x_column, color_column]):
                        dim_columns = [x_column]
                        requirements_met = True

                case SupportedPlots.heatmap:
                    metric_column = plot_config.selectbox(
                        "Measurement column", numeric_columns, help="Used for calculation", index=None
                    )
                    x_column = plot_config.selectbox("X-axis", columns, index=None)
                    y_column = plot_config.selectbox("Y-axis", columns, index=None)
                    if x_column == y_column or metric_column in [x_column, y_column]:
                        plot_display.error("The metric, X and Y columns need to be different!")
                        dim_columns = None
                        color_column = None
                        orientation = None
                        requirements_met = False
                    else:
                        if all([metric_column, x_column]):
                            dim_columns = [x_column]
                            color_column = y_column
                            orientation = None
                            requirements_met = True

                case SupportedPlots.scatter:
                    metric_column = plot_config.selectbox(
                        "Measurement column", numeric_columns, help="Used for calculation", index=None
                    )
                    x_column = plot_config.selectbox("Select X-axis dimension", columns, index=None)
                    y_column = plot_config.selectbox("Select Y-axis dimension", columns, index=None)
                    color_column = plot_config.selectbox(
                        "Color column", columns, index=0, help="A column to split the values with colors"
                    )
                    if all([metric_column, x_column, metric_column, color_column]):
                        dim_columns = [x_column, y_column]
                        orientation = None
                        requirements_met = True

                case _:
                    dim_columns = None
                    color_column = None
                    orientation = None
                    metric_column = None
                    requirements_met = False

            if not requirements_met:
                plot_display.error("Please configure the columns to be used in the chart!")
            else:
                try:
                    chart_object = get_cached_plot(
                        plot_type=plot_type,
                        metric_column=metric_column,
                        dim_columns=dim_columns,
                        color_column=color_column,
                        orientation=orientation,
                        aggregation_method=aggregation_method,
                    )

                    fig_plot = chart_object.plot
                    sql_query = chart_object.sql_query

                    fig_plot.update_layout(title=title, height=height, width=width, font_size=14, font_color="black")
                    if x_label:
                        fig_plot.update_layout(xaxis_title=x_label)
                    if y_label:
                        fig_plot.update_layout(yaxis_title=y_label)
                    with plot_display.container():
                        st.plotly_chart(fig_plot, use_container_width=False)
                    with plot_display.expander("SQL query for plot"):
                        st.code(sql_query)

                except Exception:  # NOQA
                    st.error("Something went wrong")
