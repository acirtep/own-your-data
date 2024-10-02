# TODO
# import pandas as pd
# import streamlit as st
# from sqlalchemy import select
#
# from own_your_data.database.models import CategoryUnitTypes
# from own_your_data.database.utils import get_duckdb_session
#
# session = get_duckdb_session()
#
# st.title("Work In Progress...")
# st.dataframe(
#     pd.DataFrame(session.execute(select(CategoryUnitTypes.category_unit, CategoryUnitTypes.date_created)).fetchall()),
#     hide_index=True,
# )
