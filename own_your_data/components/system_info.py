import operator
import os
import platform
from importlib import metadata

import streamlit as st

from own_your_data.charts.constants import SupportedAggregationMethods
from own_your_data.charts.definition import LineChart
from own_your_data.utils import get_duckdb_conn


@st.cache_resource()
def get_installed_pkg():
    return [
        {
            "Name": dist.name,
            "Version": dist.version,
            "Summary": dist.metadata.get("Summary"),
            "URL": dist.metadata.get("Home-page"),
        }
        for dist in metadata.distributions()
    ]


@st.cache_resource()
def get_platform_info():
    return {
        "platform": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "max_ram_size": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / pow(1024, 3),
    }


def get_system_info():
    (
        duckdb_max_size_col,
        duckdb_memory_size_col,
        duckdb_wal_size_col,
        platform_col,
        platform_release_col,
        platform_machine_col,
        max_size_col,
    ) = st.columns(7, gap="small", vertical_alignment="center")

    platform_info = get_platform_info()
    platform_col.metric("Platform", value=platform_info["platform"])
    platform_release_col.metric("Release", value=platform_info["release"])
    platform_machine_col.metric("Architecture", value=platform_info["architecture"])
    max_size_col.metric("Max RAM size (GiB)", value=round(platform_info["max_ram_size"] * 0.931323, 2))

    duckdb_conn = get_duckdb_conn()
    duckdb_size = duckdb_conn.execute("pragma database_size").df()
    duckdb_max_size_col.metric("DuckDB Max Size", value=duckdb_size["memory_limit"][0])
    duckdb_wal_size_col.metric("DuckDB WAL Size", value=duckdb_size["wal_size"][0])
    duckdb_memory_size_col.metric("DuckDB Memory Usage", value=duckdb_size["memory_usage"][0])

    memory_usage_chart = LineChart(
        duckdb_conn=duckdb_conn,
        metric_column="memory_usage",
        dim_columns=["observation_timestamp"],
        color_column=None,
        orientation=None,
        aggregation_method=SupportedAggregationMethods.none,
        table_name="database_size_monitoring",
    )
    memory_usage_plot = memory_usage_chart.plot
    memory_usage_plot.update_layout(
        title="DuckDB Memory Usage",
        font_size=14,
        font_color="black",
        xaxis_title="Observation Time",
        yaxis_title="Memory Usage in MiB",
    )
    st.plotly_chart(memory_usage_plot, use_container_width=True)

    with st.expander("Installed Python Packages"):
        installed_packages = get_installed_pkg()
        installed_packages.sort(key=operator.itemgetter("Name"))
        st.dataframe(installed_packages, column_config={"URL": st.column_config.LinkColumn()}, use_container_width=True)

    with st.expander("Logging information"):
        st.code(st.session_state.logging)
