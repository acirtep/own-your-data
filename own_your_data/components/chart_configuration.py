import streamlit as st

from own_your_data.charts.constants import SupportedAggregationMethods
from own_your_data.charts.constants import SupportedPlots
from own_your_data.charts.definition import PLOT_TYPE_TO_CHART_CLASS
from own_your_data.charts.definition import PLOT_TYPE_TO_COLOR_CLASS
from own_your_data.charts.definition import ChartConfiguration
from own_your_data.components.data_analysis import get_columns
from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import get_plotly_colors
from own_your_data.utils import timeit


def get_chart_configuration(table_name: str) -> ChartConfiguration | None:

    columns = get_columns(table_name=table_name)
    if len(columns) < 2:
        st.warning("The table chosen has only one column, the recommendation is to have at least two columns.")

    plot_type = st.radio(
        "Type",
        SupportedPlots.list(),
        horizontal=True,
        help="Type of plots, read more about them on [Plotly](https://plotly.com/python/plotly-fundamentals/)",
        key="plot_type",
    )

    aggregation_method = st.radio(
        "Calculation method", SupportedAggregationMethods.list(), horizontal=True, index=0, key="aggregation_method"
    )

    requirements_met = False
    dim_columns = None
    orientation = None
    metric_column = st.selectbox("Calculation column", columns, index=None)
    x_column = None
    if plot_type not in [SupportedPlots.sankey]:
        x_column = st.selectbox("X-axis", columns, index=None)
    y_column = None
    if plot_type not in [SupportedPlots.sankey, SupportedPlots.line, SupportedPlots.bar]:
        y_column = st.selectbox(
            "Y-axis",
            columns,
            index=None,
            help="When disabled the calculation column is on the Y-axis",
        )
    color_column = None
    if plot_type not in [SupportedPlots.sankey, SupportedPlots.heatmap]:
        color_column = st.selectbox(
            "Color column",
            columns,
            help="A column to split the values with colors",
            index=None,
        )
    match plot_type:
        case SupportedPlots.bar:
            orientation = st.radio(
                "Orientation",
                ("h", "v"),
                help="h=horizontal, v=vertical, default h",
                horizontal=True,
                index=1,
                key="orientation",
            )

            if all([metric_column, x_column]):
                dim_columns = [x_column]
                requirements_met = True

        case SupportedPlots.sankey:
            flow_columns = st.multiselect(
                "Flow columns",
                columns,
                help="Add which columns to appear in the plot in the desired order",
            )
            color_column = None
            orientation = None

            if len(flow_columns) < 2:
                st.error("There need to be at least 2 columns selected!")
                dim_columns = None
                requirements_met = False
            else:
                if all([metric_column, flow_columns]):
                    dim_columns = flow_columns
                    requirements_met = True

        case SupportedPlots.line:
            orientation = None

            if all([metric_column, x_column]):
                dim_columns = [x_column]
                requirements_met = True

        case SupportedPlots.heatmap:
            if (
                x_column
                and y_column
                and metric_column
                and (x_column == y_column or metric_column in [x_column, y_column])
            ):
                st.error("The metric, X and Y columns need to be different!")
                dim_columns = None
                color_column = None
                orientation = None
                requirements_met = False
            else:
                if all([metric_column, x_column, y_column]):
                    dim_columns = [x_column, y_column]
                    color_column = None
                    orientation = None
                    requirements_met = True

        case SupportedPlots.scatter:
            if all([metric_column, x_column, metric_column, y_column]):
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
        return None

    return ChartConfiguration(
        plot_type=plot_type,
        aggregation_method=aggregation_method,
        dim_columns=dim_columns,
        color_column=color_column,
        metric_column=metric_column,
        orientation=orientation,
        table_name=table_name,
        color_scheme=None,
        title=None,
        width=None,
        height=None,
        x_label=x_column,
        y_label=y_column,
    )


def get_chart_layout(chart_configuration: ChartConfiguration | None) -> ChartConfiguration | None:
    if not chart_configuration:
        return None
    with st.expander("Configure layout"):
        color_col, title_col, x_col, y_col, height_col = st.columns([1, 1, 1, 1, 1], vertical_alignment="center")
        chart_configuration.title = title_col.text_input("Title", value="Title")
        color_schemes = get_plotly_colors(PLOT_TYPE_TO_COLOR_CLASS.get(chart_configuration.plot_type))
        if color_schemes:
            with color_col.popover("Choose a color sequence"):
                selected_color_scheme = st.selectbox(
                    "Choose a color sequence",
                    color_schemes.keys(),
                    index=None,
                    help="""
                        Select a color for the charts.
                        More information on
                        [Plotly](https://plotly.com/python/discrete-color/#discrete-vs-continuous-color)
                    """,
                )
                if selected_color_scheme:
                    st.html(color_schemes.get(selected_color_scheme))
                    chart_configuration.color_scheme = getattr(
                        PLOT_TYPE_TO_COLOR_CLASS.get(chart_configuration.plot_type), selected_color_scheme
                    )

        if chart_configuration.plot_type not in [SupportedPlots.sankey]:
            chart_configuration.x_label = x_col.text_input("X-axis label", value=chart_configuration.x_label)

        if chart_configuration.plot_type not in [SupportedPlots.sankey]:

            chart_configuration.y_label = y_col.text_input(
                "Y-axis label", value=chart_configuration.y_label or chart_configuration.metric_column
            )
        chart_configuration.height = height_col.slider("Height", min_value=400, max_value=4000, step=50, value=400)

    return chart_configuration


@st.cache_resource
def get_cached_plot(
    plot_type: SupportedPlots,
    metric_column: str,
    dim_columns: [str],
    color_column: str | None,
    orientation: str | None,
    aggregation_method: SupportedAggregationMethods,
    table_name: str,
    color_scheme: str,
):
    duckdb_conn = get_duckdb_conn()
    chart_class = PLOT_TYPE_TO_CHART_CLASS.get(plot_type)

    if not chart_class:
        raise NotImplementedError(f"There is not implementation for {plot_type}")

    return chart_class(
        duckdb_conn=duckdb_conn,
        metric_column=metric_column,
        dim_columns=dim_columns,
        color_column=color_column,
        orientation=orientation,
        aggregation_method=aggregation_method,
        table_name=table_name,
        color_scheme=color_scheme,
    )


@timeit
def get_charts_components(chart_configuration: ChartConfiguration):
    chart_class = get_cached_plot(
        plot_type=chart_configuration.plot_type,
        metric_column=chart_configuration.metric_column,
        dim_columns=chart_configuration.dim_columns,
        color_column=chart_configuration.color_column,
        orientation=chart_configuration.orientation,
        aggregation_method=chart_configuration.aggregation_method,
        table_name=chart_configuration.table_name,
        color_scheme=chart_configuration.color_scheme,
    )

    fig_plot = chart_class.plot
    sql_query = chart_class.sql_query

    fig_plot.update_layout(
        title=chart_configuration.title,
        height=chart_configuration.height,
        width=chart_configuration.width,
        font_size=14,
        font_color="black",
    )

    if chart_configuration.x_label:
        fig_plot.update_layout(xaxis_title=chart_configuration.x_label)
    if chart_configuration.y_label:
        fig_plot.update_layout(yaxis_title=chart_configuration.y_label)

    st.plotly_chart(fig_plot, use_container_width=True)

    with st.expander("SQL query generated"):
        st.info("This is the SQL query generated based on your input in the sidebar")
        st.code(sql_query)
