import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from own_your_data.database.models import Base
from own_your_data.database.models import CategoryUnitTypes


def initial_load(session: Session):
    session.add(CategoryUnitTypes(category_unit="km"))
    session.add(CategoryUnitTypes(category_unit="kg"))
    session.add(CategoryUnitTypes(category_unit="gram"))
    session.commit()


@st.cache_resource
def get_duckdb_session() -> Session:
    engine = create_engine(
        "duckdb:///:memory:",
    )
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    initial_load(session=session)
    return session
