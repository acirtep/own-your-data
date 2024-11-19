import datetime
import inspect
import time
from functools import wraps
from pathlib import Path

import duckdb
import streamlit as st
from streamlit.logger import get_logger

logger = get_logger(__name__)


def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        if "logging" not in st.session_state:
            st.session_state.logging = ""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000
        execution_time = datetime.datetime.now().isoformat()
        function_name = func.__name__.replace("_", " ")
        chart_configuration = kwargs.get("chart_configuration")
        additional_message = (
            f" for {chart_configuration.table_name}, {chart_configuration.plot_type}" if chart_configuration else ""
        )
        st.session_state.logging = f"{execution_time}: {function_name} {additional_message} took {total_time: .4f} ms\n{st.session_state.logging}"  # NOQA
        return result

    return timeit_wrapper


@st.cache_resource
def get_duckdb_conn() -> duckdb.DuckDBPyConnection:
    duckdb_conn = duckdb.connect(f"{str(Path.home())}/own-your-data/own_your_data.db")
    duckdb_conn.sql("SET allocator_background_threads=true;")
    return duckdb_conn


def get_tables():
    duckdb_conn = get_duckdb_conn()
    return [
        table[0]
        for table in duckdb_conn.execute(
            """
                select src.table_name from
                    information_schema.tables src
                left join (select table_name,
                            end_import_datetime
                            from file_import_metadata
                            where end_import_datetime is not null
                            qualify row_number() over (partition by table_name order by id desc) = 1
                        ) fm
                    on src.table_name = fm.table_name
                order by src.table_name
                """
        ).fetchall()
    ]


def insert_database_size():
    duckdb_conn = get_duckdb_conn()
    db_size_df = duckdb_conn.execute("pragma database_size").df()  # NOQA
    duckdb_conn.execute(
        """
        insert into database_size_monitoring
        select current_timestamp,
            case split_part(wal_size, ' ', 2)
             when 'KiB' then split_part(wal_size, ' ', 1)::numeric / 1024
             when 'MiB' then split_part(wal_size, ' ', 1):: numeric
             when 'GiB' then split_part(wal_size, ' ', 1):: numeric * 1024
            end wal_size,
            case split_part(memory_usage, ' ', 2)
             when 'KiB' then split_part(memory_usage, ' ', 1)::numeric / 1024
             when 'MiB' then split_part(memory_usage, ' ', 1):: numeric
             when 'GiB' then split_part(memory_usage, ' ', 1):: numeric * 1024
            end memory_usage
        from db_size_df
    """
    )


def gather_database_size(func):
    @wraps(func)
    def gather_database_size_wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        insert_database_size()
        return result

    return gather_database_size_wrapper


@gather_database_size
@st.cache_resource
def initial_load():
    # TODO: move to database migration
    duckdb_conn = get_duckdb_conn()
    duckdb_conn.execute("create sequence if not exists file_import_metadata_seq start 1")
    duckdb_conn.execute(
        """
        create table if not exists file_import_metadata(
            id integer default nextval('file_import_metadata_seq'),
            file_name varchar,
            table_name varchar,
            start_import_datetime timestamp,
            end_import_datetime timestamp
        )
    """
    )

    duckdb_conn.execute(
        """

        create table if not exists database_size_monitoring(
            observation_timestamp timestamp primary key,
            wal_size numeric,
            memory_usage numeric
        )
    """
    )
    duckdb_conn.execute(
        """
        create table if not exists calendar_t
        as
         select range AS calendar_date,
            year(calendar_date) as calendar_year,
            month(calendar_date) as calendar_month,
            monthname(calendar_date) as calendar_month_name,
            day(calendar_date) as calendar_day,
            dayname(calendar_date) as calendar_day_name,
            case
                when quarter(calendar_date) =1 and  weekofyear(calendar_date) > 50 then 1
                else weekofyear(calendar_date)
            end as calendar_week_of_year,
            quarter(calendar_date) as calendar_quarter
         from range('2000-01-01'::date, current_date + 365, INTERVAL 1 DAY)
    """
    )
    return duckdb_conn


@st.cache_resource
def get_plotly_colors(plot_color):

    if not plot_color:
        return None
    plotly_color_schemes = inspect.getmembers(plot_color)

    # TODO: create a streamlit component
    # colors_to_html = ' ;">&#9632;</div>'.join(
    #     f'<div style="display:inline;color:{color};height:auto;margin-left:2px;width:25px;'
    #     for color in plotly_color_scheme[1]
    # )
    # color_schemes[plotly_color_scheme[0]] = (
    #     f'<div>\
    #     <input type="radio" name="color-radio" id="{plotly_color_scheme[0]}" style="display:inline">\
    #     <label for="{plotly_color_scheme[0]}" style="display:inline">\
    #     <div style="display:inline;max-width:100%;">{colors_to_html};">&#9632;</div>\
    #     </label>\
    #     </div>\
    # '
    # )

    return [
        plotly_color_scheme[0]
        for plotly_color_scheme in plotly_color_schemes
        if not (plotly_color_scheme[0].startswith("_") or not isinstance(plotly_color_scheme[1], list))
    ]


@st.cache_data
def cache_duckdb_execution(_duckdb_conn, sql_query):
    return _duckdb_conn.execute(sql_query).df()
