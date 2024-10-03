import datetime
import os
import random

import duckdb
from duckdb.typing import DOUBLE
from duckdb.typing import VARCHAR


def random_category():
    return random.choice(["FOOD", "BEVERAGE", "ALCOHOL", "SWEETS"])


def random_store():
    return random.choice(["LIDL", "CARREFOUR", "ALDI", "WALMART"])


def random_price():
    return round(random.uniform(1, 5), 2)


if __name__ == "__main__":
    duckdb_conn = duckdb.connect()
    duckdb_conn.create_function("random_category", random_category, [], VARCHAR, type="native", side_effects=True)
    duckdb_conn.create_function("random_store", random_store, [], VARCHAR, type="native", side_effects=True)
    duckdb_conn.create_function("random_price", random_price, [], DOUBLE, type="native", side_effects=True)

    file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), f"demo_csv_{datetime.datetime.now().isoformat()}.csv"
    )

    duckdb_conn.execute(
        f"""
        copy (select range::datetime as register_date,
            random_category() as category,
            random_store() as store,
            random_price() as "price now"
          from
          range(date '2022-01-31 00:00:00', date '2024-12-31 00:00:00', interval '1' hour)    ,
          generate_series(1, 1)) to '{file_path}'
        """
    )
