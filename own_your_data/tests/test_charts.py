from io import BytesIO
from pathlib import Path

import duckdb
import pytest

from own_your_data.charts.charts import BarChart
from own_your_data.charts.charts import HeatMapChart
from own_your_data.charts.charts import LineChart
from own_your_data.charts.charts import SankeyChart
from own_your_data.charts.charts import ScatterChart
from own_your_data.charts.constants import SupportedAggregationMethods
from own_your_data.charts.import_file import finalize_import
from own_your_data.charts.import_file import get_auto_column_expressions
from own_your_data.charts.import_file import import_csv

test_file_path = f"{Path(__file__).parent}/test_csv.csv"


@pytest.fixture(scope="module")
def duckdb_conn_with_final_csv_data():
    duckdb_conn = duckdb.connect()
    with open(test_file_path, "r") as f:
        import_csv(duckdb_conn=duckdb_conn, data_source=BytesIO(f.read().encode()))
        auto_column_expressions = get_auto_column_expressions(duckdb_conn=duckdb_conn)
        finalize_import(duckdb_conn=duckdb_conn, auto_column_expressions=auto_column_expressions)
    return duckdb_conn


@pytest.mark.parametrize("aggregation", SupportedAggregationMethods.list())
def test_generate_bar_chart(duckdb_conn_with_final_csv_data, aggregation):
    bar_chart = BarChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Price Now",
        dim_columns=["Register Date Date Auto"],
        color_column="Register Date Day Name Auto",
        orientation="h",
        aggregation_method=aggregation,
    )
    fig_plot = bar_chart.plot
    assert fig_plot
    assert "Monday" in [fig_plot_data["name"] for fig_plot_data in fig_plot.data]


@pytest.mark.parametrize("aggregation", SupportedAggregationMethods.list())
def test_generate_sankey_chart(duckdb_conn_with_final_csv_data, aggregation):
    sankey_chart = SankeyChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Price Now",
        dim_columns=["Register Date Month Name Auto", "Register Date Day Name Auto"],
        color_column=None,
        orientation=None,
        aggregation_method=aggregation,
    )
    fig_plot = sankey_chart.plot
    assert fig_plot
    labels = fig_plot.data[0]["node"]["label"].tolist()
    assert len(labels) == 7 + 12  # 7 day names and 12 month names
    assert fig_plot.data[0]["node"]["x"][labels.index("January")] == 0.001
    assert fig_plot.data[0]["node"]["y"][labels.index("January")] == 0.001
    assert fig_plot.data[0]["node"]["x"][labels.index("Monday")] == 0.5
    assert fig_plot.data[0]["node"]["y"][labels.index("Monday")] == 0.001


@pytest.mark.parametrize("aggregation", SupportedAggregationMethods.list())
def test_generate_line_chart(duckdb_conn_with_final_csv_data, aggregation):
    line_chart = LineChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Price Now",
        dim_columns=["Register Date Date Auto"],
        color_column="Register Date Day Name Auto",
        orientation=None,
        aggregation_method=aggregation,
    )
    fig_plot = line_chart.plot
    assert fig_plot
    assert "Monday" in [fig_plot_data["name"] for fig_plot_data in fig_plot.data]


@pytest.mark.parametrize("aggregation", SupportedAggregationMethods.list())
def test_generate_heatmap_chart(duckdb_conn_with_final_csv_data, aggregation):
    heatmap_chart = HeatMapChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Price Now",
        dim_columns=["Register Date Day Name Auto"],
        color_column="Register Date Month Name Auto",
        orientation=None,
        aggregation_method=aggregation,
    )
    fig_plot = heatmap_chart.plot
    assert fig_plot
    assert fig_plot.data[0]["x"][0] == "Monday"
    assert fig_plot.data[0]["y"][0] == "January"


@pytest.mark.parametrize("aggregation", SupportedAggregationMethods.list())
def test_generate_scatter_chart(duckdb_conn_with_final_csv_data, aggregation):
    scatter_chart = ScatterChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Price Now",
        dim_columns=["Register Date Day Name Auto", "Register Date Month Name Auto"],
        color_column="Store",
        orientation=None,
        aggregation_method=aggregation,
    )
    assert scatter_chart.plot
