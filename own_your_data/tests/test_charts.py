from io import BytesIO
from pathlib import Path
from unittest import mock

import pytest

from own_your_data.charts.charts import BarChart
from own_your_data.charts.charts import HeatMapChart
from own_your_data.charts.charts import LineChart
from own_your_data.charts.charts import SankeyChart
from own_your_data.charts.charts import ScatterChart
from own_your_data.charts.constants import SupportedAggregationMethods
from own_your_data.components.import_file import import_uploaded_file
from own_your_data.components.import_file import process_imported_data

test_file_path = f"{Path(__file__).parent}/test_csv.csv"


@pytest.fixture(scope="module")
def table_name():
    return "test_chart_table_name"


@pytest.fixture(scope="module")
def final_table_name(table_name):
    return f"{table_name}_t"


@pytest.fixture(scope="module", autouse=True)
def duckdb_conn_with_final_csv_data(table_name, duckdb_conn):
    with mock.patch("own_your_data.components.import_file.get_duckdb_conn", return_value=duckdb_conn), mock.patch(
        "own_your_data.utils.get_duckdb_conn", return_value=duckdb_conn
    ):
        with open(test_file_path, "r") as f:
            import_uploaded_file(
                data_source=BytesIO(f.read().encode()),
                table_name=table_name,
                file_name="test_csv.csv",
            )
            process_imported_data(table_name)
    return duckdb_conn


@pytest.mark.parametrize("aggregation", SupportedAggregationMethods.list())
def test_generate_bar_chart(duckdb_conn_with_final_csv_data, aggregation, final_table_name):
    bar_chart = BarChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Amount In EUR",
        dim_columns=["Register Date Date Auto"],
        color_column="Register Date Day Name Auto",
        orientation="h",
        aggregation_method=aggregation,
        table_name=final_table_name,
    )
    fig_plot = bar_chart.plot
    assert fig_plot
    assert "Monday" in [fig_plot_data["name"] for fig_plot_data in fig_plot.data]


@pytest.mark.parametrize("aggregation", SupportedAggregationMethods.list())
def test_generate_sankey_chart(duckdb_conn_with_final_csv_data, aggregation, final_table_name):
    sankey_chart = SankeyChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Amount In EUR",
        dim_columns=["Register Date Month Name Auto", "Register Date Day Name Auto"],
        color_column=None,
        orientation=None,
        aggregation_method=aggregation,
        table_name=final_table_name,
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
def test_generate_line_chart(duckdb_conn_with_final_csv_data, aggregation, final_table_name):
    line_chart = LineChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Amount In EUR",
        dim_columns=["Register Date Date Auto"],
        color_column="Register Date Day Name Auto",
        orientation=None,
        aggregation_method=aggregation,
        table_name=final_table_name,
    )
    fig_plot = line_chart.plot
    assert fig_plot
    assert "Monday" in [fig_plot_data["name"] for fig_plot_data in fig_plot.data]


@pytest.mark.parametrize("aggregation", SupportedAggregationMethods.list())
def test_generate_heatmap_chart(duckdb_conn_with_final_csv_data, aggregation, final_table_name):
    heatmap_chart = HeatMapChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Amount In EUR",
        dim_columns=["Register Date Day Name Auto"],
        color_column="Register Date Month Name Auto",
        orientation=None,
        aggregation_method=aggregation,
        table_name=final_table_name,
    )
    fig_plot = heatmap_chart.plot
    assert fig_plot
    assert fig_plot.data[0]["x"][0] == "Monday"
    assert fig_plot.data[0]["y"][0] == "January"


@pytest.mark.parametrize("aggregation", SupportedAggregationMethods.list())
def test_generate_scatter_chart(duckdb_conn_with_final_csv_data, aggregation, final_table_name):
    scatter_chart = ScatterChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Amount In EUR",
        dim_columns=["Register Date Day Name Auto", "Register Date Month Name Auto"],
        color_column="Store",
        orientation=None,
        aggregation_method=aggregation,
        table_name=final_table_name,
    )
    assert scatter_chart.plot
