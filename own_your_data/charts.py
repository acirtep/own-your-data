import plotly.express as px
import plotly.graph_objects as go
from duckdb import DuckDBPyConnection
from pandas import DataFrame
from plotly.graph_objs import Figure

from own_your_data.constants import DEFAULT_METRIC_COLUMN
from own_your_data.database.helpers import get_order_clause


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
            order by {get_order_clause(column_name=self.dim_columns[0])},
                {get_order_clause(column_name=self.color_column)}
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
            order by {get_order_clause(column_name=self.dim_columns[0])},
                {get_order_clause(column_name=self.color_column)}
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
    def get_node_info(self):
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
                    select * from ({union_cubes})
                ),
                label_grouping as (
                    -- retrieve per label the first occuring grouping set as source
                    select label, min(grouping_set) as grouping_set, sum(values) as label_value
                    from (select source as label, grouping_set, values from union_cte
                        union all
                        select target as label, 1000000, values from union_cte
                    )
                    group by label
                ),
                unique_grouping_set as (
                    -- create an array with unique grouping set, to determine the position of the label
                    select array_agg(distinct grouping_set order by grouping_set) label_grouping_uq from label_grouping
                ),
                x_position as (
                    -- the X axis is equaly split depending on the number of grouping sets
                    -- eg: 4 dimensions => 4 grouping sets => [0, 0.25, 0.75, 1]
                    select label,
                        round(
                            round(1/{len(self.dim_columns)}, 3)
                                *
                            (coalesce(
                                list_position(label_grouping_uq, grouping_set),
                                {len(self.dim_columns)}::int)
                            - 1),
                        3) as label_x_position
                        from label_grouping, unique_grouping_set
                ),
                y_position as (
                    -- the Y axis (per each X position) is split depending on the number of labels within a grouping set
                    -- the starting label in a grouping set will get 0.001
                    -- the next labels in a grouping set will get the position depending on the size of the label value
                    select label,
                        lead(grouping_set) over (grouping_set_label) as next_grouping_set,
                        lag(grouping_set) over (grouping_set_label) as previous_grouping_set,
                        sum(label_value) over (partition by grouping_set) as grouping_set_total_value,
                        sum(label_value) over (
                            partition by grouping_set order by {get_order_clause('label')}
                        ) as grouping_set_running_value,
                        round(
                            case when
                                grouping_set = coalesce(next_grouping_set, grouping_set)
                                and coalesce(previous_grouping_set, -1) != grouping_set
                            then 0.001
                        else grouping_set_running_value/grouping_set_total_value
                        end, 3) label_y_position
                    from label_grouping
                    window grouping_set_label as (
                        order by grouping_set, {get_order_clause('label')}
                    )
                ),
                idx_cte as (
                    -- aggregate in an array the label and x,y positions
                    select
                        array_agg(x_position.label) as label,
                        array_agg(case
                            when label_x_position <=0 then 0.001
                            when label_x_position >=1 then 0.999
                            else label_x_position end
                        ) as label_x_position,
                        array_agg(case
                            when label_y_position<=0 then 0.001
                            when label_y_position>=1 then 0.999
                            else label_y_position end
                        ) as label_y_position
                    from x_position
                    join y_position
                    on x_position.label = y_position.label
                )
                select
                    label,
                    label_x_position,
                    label_y_position,
                    array_agg(list_position(label, source::varchar) - 1) as source,
                    array_agg(list_position(label, target::varchar) - 1) as target,
                    array_agg(values) as values
                from union_cte, idx_cte
                group by all
                """

        node_info = self.duckdb_conn.execute(self.sql_query).fetchone()

        return node_info

    def get_plot(self) -> Figure:
        label, x_position, y_position, source, target, value = self.get_node_info()
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
                        x=x_position,
                        y=y_position,
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
