import time
from functools import wraps

import duckdb
import streamlit as st


def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        if not st.get_option("logger.level") == "debug":
            return func(*args, **kwargs)
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        st.info(f"{func.__name__.replace('_', ' ')} took {total_time * 1000: .4f} ms")
        return result

    return timeit_wrapper


@st.cache_resource
def get_duckdb_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()
