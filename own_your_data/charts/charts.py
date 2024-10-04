import plotly.express as px
import plotly.graph_objects as go
from duckdb import DuckDBPyConnection
from pandas import DataFrame
from plotly.graph_objs import Figure

from own_your_data.charts.constants import SupportedAggregationMethods
from own_your_data.charts.helpers import get_order_clause
from own_your_data.utils import timeit


class BaseChart:

    def __init__(
        self,
        duckdb_conn: DuckDBPyConnection,
        metric_column: str,
        dim_columns: [str],
        color_column: str | None,
        orientation: str | None,
        aggregation_method: str = SupportedAggregationMethods.count.value,
    ):
        self.duckdb_conn = duckdb_conn
        self.metric_column = metric_column
        self.dim_columns = dim_columns
        self.color_column = color_column
        self.orientation = orientation
        self.aggregation_method = aggregation_method

        cast_expression = (
            f'"{metric_column}"'
            if self.aggregation_method == SupportedAggregationMethods.count
            else f'try_cast("{metric_column}" as decimal)'
        )
        self.agg_expression = f"round({self.aggregation_method}({cast_expression}), 2)"
        self.where_expression = f"where {cast_expression} is not null"

        self.sql_query = self.get_sql_query()
        self.data = self.get_data()
        self.plot = self.get_plot()

    @timeit
    def get_sql_query(self) -> str:
        return f"""
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

    @timeit
    def get_data(self) -> DataFrame:
        return self.duckdb_conn.execute(self.sql_query).df()

    @timeit
    def get_plot(self) -> Figure:
        pass


class BarChart(BaseChart):

    @timeit
    def get_plot(self) -> Figure:
        if self.orientation == "v":
            return px.bar(
                data_frame=self.data,
                x=self.dim_columns[0],
                y=self.metric_column,
                orientation=self.orientation,
                color=self.color_column,
            )
        return px.bar(
            data_frame=self.data,
            x=self.metric_column,
            y=self.dim_columns[0],
            orientation=self.orientation,
            color=self.color_column,
        )


class LineChart(BaseChart):

    @timeit
    def get_plot(self) -> Figure:
        return px.line(data_frame=self.data, x=self.dim_columns[0], y=self.metric_column, color=self.color_column)


class SankeyChart(BaseChart):

    @timeit
    def get_sql_query(self) -> str:
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

        return f"""
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

    @timeit
    def get_plot(self) -> Figure:
        unpacked_data = self.data.to_dict(orient="records")[0]
        fig = Figure(
            data=[
                go.Sankey(
                    orientation=self.orientation,
                    valueformat=".0f",
                    textfont=dict(color="black", size=12),
                    node=dict(
                        pad=10,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=unpacked_data["label"],
                        color="rgb(228, 241, 225)",
                        x=unpacked_data["label_x_position"],
                        y=unpacked_data["label_y_position"],
                    ),
                    link=dict(
                        source=unpacked_data["source"],
                        target=unpacked_data["target"],
                        value=unpacked_data["values"],
                        color=["rgb(99, 166, 160)" for i in range(0, len(unpacked_data["source"]))],
                    ),
                )
            ]
        )

        return fig


class HeatMapChart(BaseChart):

    @timeit
    def get_plot(self) -> Figure:
        pivoted_data = self.data.pivot_table(
            index=self.color_column, columns=self.dim_columns[0], values=self.metric_column, sort=False
        ).fillna(0)

        fig = px.imshow(
            pivoted_data.to_numpy(),
            labels=dict(x=self.dim_columns[0], y=self.color_column, color=self.metric_column),
            x=list(pivoted_data.columns),
            y=list(pivoted_data.index),
            color_continuous_scale="mint",
            text_auto=".2f",
            aspect="auto",
        )
        fig.update_xaxes(side="top")

        return fig
