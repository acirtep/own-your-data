import streamlit as st

from own_your_data.charts.constants import SupportedAggregationMethods
from own_your_data.charts.constants import SupportedPlots
from own_your_data.charts.definition import PLOT_TYPE_TO_CHART_CLASS
from own_your_data.charts.definition import PLOT_TYPE_TO_COLOR_CLASS
from own_your_data.charts.definition import ChartConfiguration
from own_your_data.components.data_analysis import get_columns
from own_your_data.utils import cache_duckdb_execution
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
    if plot_type not in [SupportedPlots.sankey, SupportedPlots.world_map, SupportedPlots.pie]:
        x_column = st.selectbox("X-axis", columns, index=None)
    y_column = None
    if plot_type not in [
        SupportedPlots.sankey,
        SupportedPlots.line,
        SupportedPlots.bar,
        SupportedPlots.world_map,
        SupportedPlots.pie,
    ]:
        y_column = st.selectbox(
            "Y-axis",
            columns,
            index=None,
            help="When disabled the calculation column is on the Y-axis",
        )
    color_column = None
    if plot_type not in [SupportedPlots.sankey, SupportedPlots.heatmap, SupportedPlots.world_map, SupportedPlots.pie]:
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

        case SupportedPlots.world_map:
            x_column = st.selectbox(
                "Country column",
                columns,
                index=None,
                help="""Select the column which contains the country code
                in [alpha 3 format](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3)""",
            )
            if all([metric_column, x_column]):
                dim_columns = [x_column]
                requirements_met = True

        case SupportedPlots.pie:
            x_column = st.selectbox("Dimension", columns, index=None)
            if all([metric_column, x_column]):
                dim_columns = [x_column]
                requirements_met = True

        case _:
            dim_columns = None
            color_column = None
            orientation = None
            metric_column = None
            requirements_met = False

    if not requirements_met:
        return None

    filter_column = st.selectbox("Filter on", columns, index=None)
    filter_value = None

    if filter_column:
        duckdb_conn = get_duckdb_conn()
        filter_value = st.selectbox(
            "Exact match on",
            cache_duckdb_execution(
                duckdb_conn,
                f"""
                select "{filter_column}" from (
                    select "{filter_column}", count(*) as cnt
                    from {table_name}
                    group by 1
                    ) as src
                order by cnt desc
                limit 100
            """,
            ),
            index=None,
            key="exact-match-on",
            help="The top 100 most encountered values",
        )

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
        color_label=color_column,
        filter_column=filter_column,
        filter_value=str(filter_value) if filter_value else None,
    )


def get_chart_layout(chart_configuration: ChartConfiguration | None) -> ChartConfiguration | None:
    if not chart_configuration:
        return None
    with st.expander("Configure layout"):
        color_legend_col, color_col, title_col, x_col, y_col, color_label_col, height_col, hide_legend_col = st.columns(
            [0.5, 1, 1, 1, 1, 1, 1, 0.5], vertical_alignment="bottom", gap="small"
        )
        chart_configuration.title = title_col.text_input("Title", value="Title")
        plot_color_scheme = PLOT_TYPE_TO_COLOR_CLASS.get(chart_configuration.plot_type)
        if plot_color_scheme:
            with color_legend_col.popover("🎨"):
                st.info(
                    "Here is a preview of color palettes available.\
                    Choose one from the list :green[Choose a color sequence]"
                )
                st.plotly_chart(plot_color_scheme.swatches())

            plotly_colors = get_plotly_colors(plot_color_scheme)
            selected_color_scheme = color_col.selectbox(
                "Choose a color sequence",
                plotly_colors,
                index=None,
                help="""
                    Select a color for the charts.
                    More information on
                    [Plotly](https://plotly.com/python/discrete-color/#discrete-vs-continuous-color). \n
                    In order to avoid the same color to be used by different values, the chart will automatically
                    use the default colors. For example, `Plotly` palette has 10 colors and will not be used to
                    color the chart which has more than 10 values on the color column.
                """,
            )
            if selected_color_scheme:
                chart_configuration.color_scheme = getattr(plot_color_scheme, selected_color_scheme)

        if chart_configuration.plot_type == SupportedPlots.sankey:
            node_color = color_legend_col.color_picker("🎨 Node", value="#D4E016")
            link_color = color_col.color_picker("🎨 Link", value="#30A852")
            chart_configuration.color_scheme = [node_color, link_color]

        if chart_configuration.plot_type not in [SupportedPlots.sankey, SupportedPlots.world_map, SupportedPlots.pie]:
            chart_configuration.x_label = x_col.text_input("X-axis label", value=chart_configuration.x_label)

        if chart_configuration.plot_type not in [SupportedPlots.sankey, SupportedPlots.world_map, SupportedPlots.pie]:

            chart_configuration.y_label = y_col.text_input(
                "Y-axis label", value=chart_configuration.y_label or chart_configuration.metric_column
            )

        if chart_configuration.plot_type in [SupportedPlots.heatmap, SupportedPlots.world_map]:

            chart_configuration.color_label = color_label_col.text_input(
                "Color axis label", value=chart_configuration.color_column or chart_configuration.metric_column
            )

        chart_configuration.height = height_col.slider("Height", min_value=400, max_value=4000, step=50, value=400)

        chart_configuration.hide_legend = hide_legend_col.checkbox("Hide legend")
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
    color_scheme: list[str] | None,
    filter_column: str | None,
    filter_value: list[str] | None,
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
        filter_column=filter_column,
        filter_value=filter_value,
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
        filter_column=chart_configuration.filter_column,
        filter_value=chart_configuration.filter_value,
    )

    fig_plot = chart_class.plot
    sql_query = chart_class.sql_query

    fig_plot.update_layout(
        title={"text": chart_configuration.title},
        height=chart_configuration.height,
        width=chart_configuration.width,
        font_size=14,
        font_color="black",
        showlegend=not chart_configuration.hide_legend,
        coloraxis_colorbar={"title": chart_configuration.color_label},
    )

    if chart_configuration.x_label:
        fig_plot.update_layout(xaxis_title=chart_configuration.x_label)
    if chart_configuration.y_label:
        fig_plot.update_layout(yaxis_title=chart_configuration.y_label)

    if chart_class.x_integer:
        fig_plot.update_xaxes(type="category")
    if chart_class.y_integer:
        fig_plot.update_yaxes(type="category")

    st.plotly_chart(fig_plot, use_container_width=True)

    with st.expander("SQL query generated"):
        st.info("This is the SQL query generated based on your input in the sidebar")
        st.code(sql_query)
