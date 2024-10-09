import streamlit as st

from own_your_data.charts.charts import PLOT_TYPE_TO_CHART_CLASS
from own_your_data.charts.constants import SupportedPlots
from own_your_data.utils import get_duckdb_conn


@st.cache_resource
def get_cached_plot(
    plot_type: SupportedPlots,
    metric_column: str,
    dim_columns: [str],
    color_column: str | None,
    orientation: str | None,
    aggregation_method: str,
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
    )
