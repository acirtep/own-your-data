import streamlit as st

from own_your_data.charts.charts import ChartConfiguration
from own_your_data.charts.constants import SupportedPlots
from own_your_data.components.helpers import get_cached_plot


def get_charts_components(chart_configuration: ChartConfiguration):
    chart_object = get_cached_plot(
        plot_type=chart_configuration.plot_type,
        metric_column=chart_configuration.metric_column,
        dim_columns=chart_configuration.dim_columns,
        color_column=chart_configuration.color_column,
        orientation=chart_configuration.orientation,
        aggregation_method=chart_configuration.aggregation_method,
        table_name=chart_configuration.table_name,
    )

    fig_plot = chart_object.plot
    sql_query = chart_object.sql_query

    fig_plot.update_layout(
        title=chart_configuration.title,
        height=chart_configuration.height,
        width=chart_configuration.width,
        font_size=14,
        font_color="black",
    )
    if chart_configuration.x_label:
        fig_plot.update_layout(xaxis_title=chart_configuration.x_label)
    if chart_configuration.y_label:
        fig_plot.update_layout(yaxis_title=chart_configuration.y_label)

    if chart_configuration.plot_type == SupportedPlots.line:
        fig_plot.update_xaxes(
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
        fig_plot.update_layout(
            template="plotly_dark",
            xaxis_rangeselector_font_color="black",
            xaxis_rangeselector_activecolor="rgb(228, 241, 225)",
            xaxis_rangeselector_bgcolor="rgb(99, 166, 160)",
        )

    st.plotly_chart(fig_plot, use_container_width=True)

    with st.expander("SQL query generated"):
        st.info("This is the SQL query generated based on your input in the sidebar")
        st.code(sql_query)
