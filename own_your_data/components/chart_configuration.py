import streamlit as st

from own_your_data.charts.charts import ChartConfiguration
from own_your_data.charts.constants import SupportedAggregationMethods
from own_your_data.charts.constants import SupportedPlots
from own_your_data.components.data_analysis import get_columns


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
    x_column = st.selectbox("X-axis", columns, index=None, disabled=plot_type == SupportedPlots.sankey)
    y_column = st.selectbox(
        "Y-axis",
        columns,
        index=None,
        disabled=plot_type in [SupportedPlots.sankey, SupportedPlots.line, SupportedPlots.bar],
        help="When disabled the calculation column is on the Y-axis",
    )
    color_column = st.selectbox(
        "Color column",
        columns,
        help="A column to split the values with colors",
        index=None,
        disabled=plot_type in [SupportedPlots.sankey, SupportedPlots.heatmap],
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
                    dim_columns = [x_column]
                    color_column = y_column
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

    title = st.text_input("Title", value="Title")
    x_label = st.text_input("X-axis label", value=x_column)
    y_label = st.text_input("Y-axis label", value=y_column or metric_column)
    height = st.slider("Height", min_value=400, max_value=4000, step=50, value=400)
    width = st.slider("Width", min_value=600, max_value=3000, step=50, value=900)

    if not requirements_met:
        return None

    return ChartConfiguration(
        plot_type=plot_type,
        aggregation_method=aggregation_method,
        title=title,
        width=width,
        height=height,
        x_label=x_label,
        y_label=y_label,
        dim_columns=dim_columns,
        color_column=color_column,
        metric_column=metric_column,
        orientation=orientation,
        table_name=table_name,
    )
