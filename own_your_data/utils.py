import time
from functools import wraps

import duckdb
import streamlit as st
from streamlit.logger import get_logger

logger = get_logger(__name__)


def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        if not st.get_option("logger.level") == "debug":
            return func(*args, **kwargs)
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        logger.debug(f"{func.__name__.replace('_', ' ')} took {total_time * 1000: .4f} ms")
        return result

    return timeit_wrapper


@st.cache_resource
def get_duckdb_conn() -> duckdb.DuckDBPyConnection:
    duckdb_conn = duckdb.connect()
    duckdb_conn.execute("create sequence file_import_metadata_seq start 1")
    duckdb_conn.execute(
        """
        create table file_import_metadata(
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
        create table calendar_t
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
