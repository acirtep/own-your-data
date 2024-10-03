import plotly.express as px
import plotly.graph_objects as go
from duckdb import DuckDBPyConnection
from pandas import DataFrame
from plotly.graph_objs import Figure

from own_your_data.constants import DEFAULT_METRIC_COLUMN


class BaseChart:

    def __init__(
        self,
        duckdb_conn: DuckDBPyConnection,
        metric_column: str,
        dim_columns: [str],
        color_column: str | None,
        orientation: str,
    ):
        self.duckdb_conn = duckdb_conn
        self.metric_column = metric_column or DEFAULT_METRIC_COLUMN
        self.dim_columns = dim_columns
        self.color_column = color_column
        self.orientation = orientation

        if self.metric_column == DEFAULT_METRIC_COLUMN:
            self.agg_expression = "count(*)"
            self.where_expression = None
        else:
            self.agg_expression = f'sum("{metric_column}"::decimal)'
            self.where_expression = f'where try_cast("{metric_column}" as decimal) is not null'

        self.sql_query = None


class BarChart(BaseChart):

    def get_data(self) -> DataFrame:
        self.sql_query = f"""
            select
                {self.agg_expression} as "{self.metric_column}",
                "{self.dim_columns[0]}",
                "{self.color_column}"
            from csv_import_t
            {self.where_expression}
            group by 2,3
            order by 2,3
        """
        return self.duckdb_conn.execute(self.sql_query).df()

    def get_plot(self) -> Figure:
        if self.orientation == "v":
            return px.bar(
                data_frame=self.get_data(),
                x=self.dim_columns[0],
                y=self.metric_column,
                orientation=self.orientation,
                color=self.color_column,
            )
        return px.bar(
            data_frame=self.get_data(),
            x=self.metric_column,
            y=self.dim_columns[0],
            orientation=self.orientation,
            color=self.color_column,
        )


class LineChart(BaseChart):
    def get_data(self) -> DataFrame:
        self.sql_query = f"""
            select
                {self.agg_expression} as "{self.metric_column}",
                "{self.dim_columns[0]}",
                "{self.color_column}"
            from csv_import_t
            {self.where_expression}
            group by 2,3
            order by 2,3
        """
        return self.duckdb_conn.execute(self.sql_query).df()

    def get_plot(self) -> Figure:
        return px.line(
            data_frame=self.get_data(),
            x=self.dim_columns[0],
            y=self.metric_column,
            orientation="v",
            color=self.color_column,
        )


class SankeyChart(BaseChart):
    def get_node_info(self) -> (list[float], list[str], list[int], list[int], list[int]):
        dim_col_list = " ,".join([f'"{dim_col}"' for dim_col in self.dim_columns])
        if len(self.dim_columns) <= 1:
            raise ValueError("At least 2 dimensions required!")

        cubes = ""
        union_cubes = ""

        for idx in range(0, len(self.dim_columns) - 1):
            cubes = f'("{self.dim_columns[idx]}", "{self.dim_columns[idx + 1]}"), {cubes}'
            union_cubes = f"""
            {union_cubes}
            select "{self.metric_column}" as values,
                "{self.dim_columns[idx]}" as source,
                "{self.dim_columns[idx + 1]}" as target,
                grouping_set
            from cube_cte
            where "{self.dim_columns[idx]}" is not null
                and "{self.dim_columns[idx + 1]}" is not null
            \n
            {'union all' if idx < len(self.dim_columns) - 2 else ""}
            """
        self.sql_query = f"""
                with cube_cte as (
                    -- calculate the metric aggregate for each set of 2 dimensions, in the order selected
                    select
                        {self.agg_expression} as "{self.metric_column}",
                        {dim_col_list},
                       GROUPING_ID({dim_col_list}) AS grouping_set
                    from csv_import_t
                    {self.where_expression}
                    GROUP BY GROUPING SETS ({cubes})
                ),
                union_cte as (
                    -- union all combinations of grouping sets
                    {union_cubes}
                ),
                label_grouping as (select label, min(grouping_set) as grouping_set
                    from (select source as label, grouping_set from union_cte
                        union all
                        select target as label, 1000000 from union_cte
                    )
                    group by label),
                unique_grouping_set as (
                    select array_agg(distinct grouping_set order by grouping_set) label_grouping_uq from label_grouping
                ),
                idx_cte as (
                    -- get all the distinct values from the dimensions (labels)
                    select
                        array_agg(label) as label,
                        array_agg(grouping_position) as grouping_position
                        from (
                            select label,
                            coalesce(
                                list_position(label_grouping_uq, grouping_set),
                                {len(self.dim_columns)}::int
                            ) as grouping_position
                        from label_grouping, unique_grouping_set)
                )
                select
                    label,
                    grouping_position,
                    array_agg(list_position(label, source::varchar) - 1) as source,
                    array_agg(list_position(label, target::varchar) - 1) as target,
                    array_agg(values) as values
                from union_cte, idx_cte
                group by all
                """

        node_info = self.duckdb_conn.execute(self.sql_query).fetchone()

        return node_info

    def get_plot(self) -> Figure:
        label, grouping_position, source, target, value = self.get_node_info()
        x_equal_split = round(1 / len(self.dim_columns), 2)

        return Figure(
            data=[
                go.Sankey(
                    orientation=self.orientation,
                    valueformat=".0f",
                    node=dict(
                        pad=10,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=label,
                        color="rgb(204, 80, 62)",
                        x=[x_equal_split * (_ - 1) for _ in grouping_position],
                    ),
                    link=dict(
                        source=source,
                        target=target,
                        value=value,
                        color=["rgb(221, 204, 119)" for i in range(0, len(source))],
                    ),
                )
            ]
        )
