from io import BytesIO
from pathlib import Path

import duckdb
import pytest

from own_your_data.charts import BarChart
from own_your_data.charts import LineChart
from own_your_data.charts import SankeyChart
from own_your_data.database.helpers import finalize_import
from own_your_data.database.helpers import get_auto_column_expressions
from own_your_data.database.helpers import import_csv

test_file_path = f"{Path(__file__).parent}/test_csv.csv"


@pytest.fixture(scope="module")
def duckdb_conn_with_final_csv_data():
    duckdb_conn = duckdb.connect()
    with open(test_file_path, "r") as f:
        import_csv(duckdb_conn=duckdb_conn, data_source=BytesIO(f.read().encode()))
        auto_column_expressions = get_auto_column_expressions(duckdb_conn=duckdb_conn)
        finalize_import(duckdb_conn=duckdb_conn, auto_column_expressions=auto_column_expressions)
    return duckdb_conn


def test_generate_bar_chart(duckdb_conn_with_final_csv_data):
    bar_chart = BarChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Price Now",
        dim_columns=["Register Date Day Name Auto"],
        color_column="Register Date Day Name Auto",
        orientation="h",
    )
    fig_plot = bar_chart.get_plot()
    assert fig_plot
    assert "Monday" in [fig_plot_data["name"] for fig_plot_data in fig_plot.data]


def test_generate_sankey_chart(duckdb_conn_with_final_csv_data):
    sankey_chart = SankeyChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Price Now",
        dim_columns=["Register Date Month Name Auto", "Register Date Day Name Auto"],
        color_column=None,
        orientation="h",
    )
    fig_plot = sankey_chart.get_plot()
    assert fig_plot
    # 7 day names and 12 month names
    assert len(fig_plot.data[0]["node"]["label"]) == 7 + 12
    assert fig_plot.data[0]["node"]["x"][fig_plot.data[0]["node"]["label"].index("January")] == 0.001
    assert fig_plot.data[0]["node"]["y"][fig_plot.data[0]["node"]["label"].index("January")] == 0.001
    assert fig_plot.data[0]["node"]["x"][fig_plot.data[0]["node"]["label"].index("Monday")] == 0.5
    assert fig_plot.data[0]["node"]["y"][fig_plot.data[0]["node"]["label"].index("Monday")] == 0.001


def test_generate_line_chart(duckdb_conn_with_final_csv_data):
    line_chart = LineChart(
        duckdb_conn=duckdb_conn_with_final_csv_data,
        metric_column="Price Now",
        dim_columns=["Register Date"],
        color_column="Register Date Day Name Auto",
        orientation="v",
    )
    fig_plot = line_chart.get_plot()
    assert fig_plot
    assert "Monday" in [fig_plot_data["name"] for fig_plot_data in fig_plot.data]
