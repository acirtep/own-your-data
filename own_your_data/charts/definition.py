from dataclasses import dataclass
from itertools import chain
from typing import Optional

import plotly.express as px
import plotly.graph_objects as go
from duckdb import DuckDBPyConnection
from plotly.graph_objs import Figure

from own_your_data.charts.constants import PRIMARY_COLOR
from own_your_data.charts.constants import SECONDARY_COLOR
from own_your_data.charts.constants import SupportedAggregationMethods
from own_your_data.charts.constants import SupportedPlots
from own_your_data.charts.helpers import get_order_clause
from own_your_data.utils import cache_duckdb_execution
from own_your_data.utils import timeit


class BaseChart:

    def __init__(
        self,
        duckdb_conn: DuckDBPyConnection,
        metric_column: str,
        dim_columns: [str],
        color_column: str | None,
        orientation: str | None,
        table_name: str,
        aggregation_method: str = SupportedAggregationMethods.count.value,
        color_scheme: list[str] | None = None,
    ):
        self.duckdb_conn = duckdb_conn
        self.metric_column = metric_column
        self.dim_columns = dim_columns
        self.color_column = color_column
        self.orientation = orientation
        self.aggregation_method = aggregation_method
        self.table_name = table_name
        self.color_scheme = color_scheme

        cast_expression = (
            f'"{metric_column}"'
            if self.aggregation_method == SupportedAggregationMethods.count
            else f'try_cast("{metric_column}" as decimal)'
        )
        self.agg_expression = (
            f'"{metric_column}"'
            if self.aggregation_method == SupportedAggregationMethods.none
            else f"round({self.aggregation_method}({cast_expression}), 2)"
        )
        self.where_expression = f"where {cast_expression} is not null"
        self.group_by = "" if self.aggregation_method == SupportedAggregationMethods.none else "group by all"
        self.validate_color_scheme()
        self.sql_query = self.get_sql_query()
        self.data = self.get_data()
        self.category_orders = self.get_category_orders()
        self.plot = self.get_plot()

    @timeit
    def get_sql_query(self) -> str:
        if not self.color_column:
            return f"""
                select
                {self.agg_expression} as "{self.metric_column}",
                "{self.dim_columns[0]}",
                {get_order_clause(self.dim_columns[0])} as "ordered xyz"
            from {self.table_name}
            {self.where_expression}
            {self.group_by}
            order by {get_order_clause(self.dim_columns[0])}
            """
        return f"""
            select
                {self.agg_expression} as "{self.metric_column}",
                "{self.dim_columns[0]}",
                "{self.color_column}",
                {get_order_clause(self.dim_columns[0])},
                {get_order_clause(self.color_column)}
            from {self.table_name}
            {self.where_expression}
            {self.group_by}
            order by {get_order_clause(self.dim_columns[0])},
                {get_order_clause(self.color_column)}
        """

    @timeit
    def get_data(self):
        return cache_duckdb_execution(_duckdb_conn=self.duckdb_conn, sql_query=self.sql_query)

    @timeit
    def get_category_orders(self):
        category_order = {}
        for column in chain(self.dim_columns, [self.color_column]):
            if not column:
                continue
            unique_values_df = cache_duckdb_execution(
                _duckdb_conn=self.duckdb_conn,
                sql_query=f"""
                        select distinct "{column}"
                        from {self.table_name} src
                        where try_cast("{column}" as numeric) is null
                        and try_cast("{column}" as date) is null
                        order by {get_order_clause(column)}
                    """,
            )
            if not unique_values_df.empty:
                category_order[column] = unique_values_df[column].tolist()
        return category_order

    @timeit
    def get_plot(self) -> Figure:
        pass

    @timeit
    def validate_color_scheme(self):
        if not self.color_column:
            return
        if not self.color_scheme:
            return
        more_values_than_color = cache_duckdb_execution(
            _duckdb_conn=self.duckdb_conn,
            sql_query=f"""
            select count(distinct "{self.color_column}") as count_records
            from {self.table_name}
            having count(distinct "{self.color_column}") > {len(self.color_scheme)}
        """,
        )
        if not more_values_than_color.empty:
            self.color_scheme = None


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
                category_orders=self.category_orders,
                color_discrete_sequence=self.color_scheme,
            )
        return px.bar(
            data_frame=self.data,
            x=self.metric_column,
            y=self.dim_columns[0],
            orientation=self.orientation,
            color=self.color_column,
            category_orders=self.category_orders,
            color_discrete_sequence=self.color_scheme,
        )


class LineChart(BaseChart):

    @timeit
    def get_plot(self) -> Figure:
        fig = px.line(
            data_frame=self.data,
            x=self.dim_columns[0],
            y=self.metric_column,
            color=self.color_column,
            category_orders=self.category_orders,
            color_discrete_sequence=self.color_scheme,
            # Issue in Plotly: https://stackoverflow.com/questions/73321843/plotly-weekly-monthly-range-selector-buttons-not-working-on-time-series-data  # NOQA
            # markers=True,
            # symbol=self.color_column,
        )

        fig.update_xaxes(
            rangeslider_visible=False,
            rangemode="tozero",
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=1, label="1d", step="day", stepmode="backward"),
                        dict(count=7, label="1w", step="day", stepmode="backward"),
                        dict(count=14, label="2w", step="day", stepmode="backward"),
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=3, label="3m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all"),
                    ]
                )
            ),
        )
        fig.update_layout(
            template="plotly_dark",
            xaxis_rangeselector_font_color="black",
            xaxis_rangeselector_activecolor=SECONDARY_COLOR,
            xaxis_rangeselector_bgcolor=PRIMARY_COLOR,
        )
        return fig


class SankeyChart(BaseChart):
    def __init__(
        self,
        duckdb_conn: DuckDBPyConnection,
        metric_column: str,
        dim_columns: [str],
        color_column: str | None,
        orientation: str | None,
        table_name: str,
        aggregation_method: str = SupportedAggregationMethods.count.value,
        color_scheme: Optional[px.colors.sequential] = px.colors.sequential.Mint,
    ):
        super().__init__(
            duckdb_conn=duckdb_conn,
            metric_column=metric_column,
            dim_columns=dim_columns,
            color_column=color_column,
            orientation=orientation,
            aggregation_method=(
                SupportedAggregationMethods.sum.value
                if aggregation_method == SupportedAggregationMethods.none
                else aggregation_method
            ),
            table_name=table_name,
            color_scheme=color_scheme,
        )

    @timeit
    def get_sql_query(self) -> str:
        dim_col_list = " ,".join([f'"{dim_col}"' for dim_col in self.dim_columns])

        cubes = ""
        union_cubes = ""

        for idx in range(0, len(self.dim_columns) - 1):
            cubes = f'("{self.dim_columns[idx]}", "{self.dim_columns[idx + 1]}"), {cubes}'
            union_cubes = f"""
            {union_cubes}
            select "{self.metric_column}" as values,
                concat('{self.dim_columns[idx]}',
                    concat('-dummy-placeholder-',"{self.dim_columns[idx]}")
                ) as source,
                concat('{self.dim_columns[idx + 1]}',
                    concat('-dummy-placeholder-',"{self.dim_columns[idx + 1]}")
                ) as target,
                grouping_set
            from cube_cte
            where "{self.dim_columns[idx]}" is not null
                and "{self.dim_columns[idx + 1]}" is not null
                and "{self.metric_column}" > 0
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
                    from {self.table_name}
                    {self.where_expression}
                    GROUP BY GROUPING SETS ({cubes})
                ),
                union_cte as (
                    -- union all combinations of grouping sets
                    select * from ({union_cubes})
                ),
                label_grouping as (
                    -- retrieve per label the first occuring grouping set as source
                    select label,
                        min(grouping_set) as grouping_set,
                        sum(values) as label_value,
                        split_part(label, '-dummy-placeholder-', 2) as label_without_placeholder
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
                        count(label_value) over (partition by grouping_set) as number_labels_in_group,
                        count(label_value) over (
                            partition by grouping_set order by {get_order_clause('label_without_placeholder')}
                        ) as number_labels_to_label,
                        max(label_value) over (partition by grouping_set) max_value,
                        min(label_value) over (partition by grouping_set) min_value,
                        sum(label_value) over (partition by grouping_set) as grouping_set_total_value,
                        sum(label_value) over (
                            partition by grouping_set order by {get_order_clause('label_without_placeholder')}
                        ) as grouping_set_running_value,
                        case when number_labels_in_group <= 4
                            then 0.3
                        else 1/number_labels_in_group
                        end as starting_position,
                        case when number_labels_in_group <= 4
                            then 0.7
                        else 0.999
                        end as ending_position,
                        round(
                            case
                            when number_labels_in_group = 1 then 0.499
                            when
                                grouping_set = coalesce(next_grouping_set, grouping_set)
                                and coalesce(previous_grouping_set, -1) != grouping_set
                            then starting_position
                        else starting_position +
                            grouping_set_running_value/grouping_set_total_value/3 * (ending_position-starting_position)
                        end, 3) label_y_position
                    from label_grouping
                    window grouping_set_label as (
                        order by grouping_set, {get_order_clause('label_without_placeholder')}
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
                    list_transform(label, x -> split_part(x, '-dummy-placeholder-', 2)) as label,
                    label_x_position,
                    label_y_position,
                    array_agg(list_position(idx_cte.label, source::varchar) - 1) as source,
                    array_agg(list_position(idx_cte.label, target::varchar) - 1) as target,
                    array_agg(values) as values
                from union_cte, idx_cte
                group by all
                """

    @timeit
    def get_plot(self) -> Figure:
        unpacked_data = self.data.to_dict(orient="records")[0]
        node_color = SECONDARY_COLOR
        link_color = PRIMARY_COLOR
        if len(self.color_scheme) == 2:
            node_color = self.color_scheme[0]
            link_color = self.color_scheme[1]
        fig = Figure(
            data=[
                go.Sankey(
                    orientation=self.orientation,
                    valueformat=".0f",
                    textfont=dict(color="white", size=12),
                    node=dict(
                        pad=10,
                        thickness=20,
                        line=dict(color="green", width=0.5),
                        label=unpacked_data["label"],
                        color=node_color,
                        x=unpacked_data["label_x_position"],
                        y=unpacked_data["label_y_position"],
                    ),
                    link=dict(
                        source=unpacked_data["source"],
                        target=unpacked_data["target"],
                        value=unpacked_data["values"],
                        color=[link_color for i in range(0, len(unpacked_data["source"]))],
                    ),
                )
            ]
        )
        fig.update_traces(arrangement="snap", selector=dict(type="sankey"))
        # TODO: implement labels
        # number_columns = len(self.dim_columns)
        # for idx, dim_column in enumerate(self.dim_columns):
        #     fig.add_annotation(
        #         dict(
        #             font=dict(color=SECONDARY_COLOR, size=12),
        #             x=idx / number_columns,
        #             y=1.05,
        #             showarrow=False,
        #             text=f"<b>{dim_column.upper()}</b>",
        #         )
        #     )
        return fig


class HeatMapChart(BaseChart):

    @timeit
    def get_sql_query(self) -> str:
        return f"""
            with existing_data as (
            select
                {self.agg_expression} as "{self.metric_column}",
                "{self.dim_columns[0]}",
                "{self.dim_columns[1]}"
            from {self.table_name}
            {self.where_expression}
            {self.group_by}),
            unique_dim_col_0 as (select distinct "{self.dim_columns[0]}" from {self.table_name}
            {self.where_expression}),
            unique_dim_col1 as (select distinct "{self.dim_columns[1]}" from {self.table_name}
            {self.where_expression})
            select * from (
                select *
                from existing_data
                union all
                select distinct 0,
                    col0."{self.dim_columns[0]}",
                    col1."{self.dim_columns[1]}"
                from unique_dim_col_0 col0, unique_dim_col1 col1
                where not exists( select 1
                    from existing_data src
                    where src."{self.dim_columns[0]}" = col0."{self.dim_columns[0]}"
                    and src."{self.dim_columns[1]}" = col1."{self.dim_columns[1]}"
                    )
            ) with_fill_null
            order by {get_order_clause(self.dim_columns[1])}, {get_order_clause(self.dim_columns[0])}
        """

    @timeit
    def get_plot(self) -> Figure:
        pivoted_data = self.data.pivot_table(
            index=self.dim_columns[1], columns=self.dim_columns[0], values=self.metric_column, sort=False
        )

        fig = px.imshow(
            pivoted_data.to_numpy(),
            labels=dict(x=self.dim_columns[0], y=self.color_column, color=self.metric_column),
            x=list(pivoted_data.columns),
            y=list(pivoted_data.index),
            color_continuous_scale=self.color_scheme,
            text_auto=".2f",
            aspect="auto",
        )
        fig.update_xaxes(side="top")

        return fig


class ScatterChart(BaseChart):

    @timeit
    def validate_color_scheme(self):
        if not self.color_column:
            return

        check_color_column_numeric = cache_duckdb_execution(
            _duckdb_conn=self.duckdb_conn,
            sql_query=f"""
                select *
                from {self.table_name}
                where try_cast("{self.color_column}" as numeric) is null
                limit 1
            """,
        )
        if not check_color_column_numeric.empty:
            super().validate_color_scheme()

    @timeit
    def get_sql_query(self) -> str:
        if not self.color_column:
            return f"""
                select
                    {self.agg_expression} as "{self.metric_column}",
                    "{self.dim_columns[0]}",
                    "{self.dim_columns[1]}"
                from {self.table_name}
                {self.where_expression}
                {self.group_by}
            """
        return f"""
            select
                {self.agg_expression} as "{self.metric_column}",
                "{self.dim_columns[0]}",
                "{self.dim_columns[1]}",
                "{self.color_column}"
            from {self.table_name}
            {self.where_expression}
            {self.group_by}
        """

    @timeit
    def get_plot(self) -> Figure:
        return px.scatter(
            self.data,
            x=self.dim_columns[0],
            y=self.dim_columns[1],
            color=self.color_column,
            size=self.metric_column,
            category_orders=self.category_orders,
            color_discrete_sequence=self.color_scheme,
            color_continuous_scale=self.color_scheme,
        )


PLOT_TYPE_TO_CHART_CLASS = {
    SupportedPlots.bar: BarChart,
    SupportedPlots.line: LineChart,
    SupportedPlots.sankey: SankeyChart,
    SupportedPlots.heatmap: HeatMapChart,
    SupportedPlots.scatter: ScatterChart,
}

PLOT_TYPE_TO_COLOR_CLASS = {
    SupportedPlots.bar: px.colors.qualitative,
    SupportedPlots.line: px.colors.qualitative,
    SupportedPlots.heatmap: px.colors.sequential,
    SupportedPlots.scatter: px.colors.sequential,
    SupportedPlots.sankey: None,
}


@dataclass
class ChartConfiguration:
    table_name: str
    plot_type: SupportedPlots
    aggregation_method: SupportedAggregationMethods
    metric_column: str
    dim_columns: list[str]
    color_column: str | None
    orientation: str | None
    title: str | None
    x_label: str | None
    y_label: str | None
    height: int | None
    width: int | None
    color_scheme: list[str] | None
