import os
from io import BytesIO

import pytest

from own_your_data.charts import BarChart
from own_your_data.charts import SankeyChart
from own_your_data.pages.generate_charts import get_duckdb_conn_with_data

test_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_csv.csv")


@pytest.fixture
def duckdb_conn_with_csv_data():
    with open(test_file_path, "r") as f:
        duckdb_conn, columns = get_duckdb_conn_with_data(data_source=BytesIO(f.read().encode()))

    return duckdb_conn, columns


def test_generate_charts_get_duckdb_conn_with_data(duckdb_conn_with_csv_data):
    _, columns = duckdb_conn_with_csv_data
    assert columns == [
        "Register Date",
        "Category",
        "Price Now",
        "Day Name",
        "Register Date Month Name",
        "Register Date Day Name",
    ]


def test_generate_bar_chart(duckdb_conn_with_csv_data):
    duckdb_conn, _ = duckdb_conn_with_csv_data
    bar_chart = BarChart(
        duckdb_conn=duckdb_conn,
        metric_column="Price Now",
        dim_columns=["Register Date Day Name"],
        color_column="Register Date Day Name",
        orientation="h",
    )
    fig_plot = bar_chart.get_plot()
    assert fig_plot
    assert "Monday" in [fig_plot_data["name"] for fig_plot_data in fig_plot.data]


def test_generate_sankey_chart(duckdb_conn_with_csv_data):
    duckdb_conn, _ = duckdb_conn_with_csv_data
    sankey_chart = SankeyChart(
        duckdb_conn=duckdb_conn,
        metric_column="Price Now",
        dim_columns=["Register Date Month Name", "Register Date Day Name"],
        color_column=None,
        orientation="h",
    )
    fig_plot = sankey_chart.get_plot()
    assert fig_plot
    # 7 day names and 12 month names
    assert len(fig_plot.data[0]["node"]["label"]) == 7 + 12
