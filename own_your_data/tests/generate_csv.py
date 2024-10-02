import random

import duckdb
from duckdb.typing import DOUBLE
from duckdb.typing import VARCHAR


def random_category():
    return random.choice(["FOOD", "BEVERAGE", "ALCOHOL", "SWEETS"])


def random_price():
    return round(random.uniform(1, 5), 2)


duckdb_conn = duckdb.connect()
duckdb_conn.create_function("random_category", random_category, [], VARCHAR, type="native", side_effects=True)
duckdb_conn.create_function("random_price", random_price, [], DOUBLE, type="native", side_effects=True)


duckdb_conn.execute(
    """
    copy (select range::date as register_date,
        random_category() as category,
        random_price() as "price now",
        case isodow(range::date)  when 1 then 'Monday'
                when 2 then 'Tuesday'
                when 3 then 'Wednesday'
                when 4 then 'Thursday'
                when 5 then 'Friday'
                when 6 then 'Saturday'
                when 7 then 'Sunday'
                end
                as "day Name"
      from
      range(date '2022-01-31', date '2024-12-31', interval '1' day)    ,
      generate_series(1, 1)) to './test_csv.csv'
"""
)
