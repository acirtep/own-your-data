import streamlit as st

from own_your_data.components import about
from own_your_data.components import generate_charts

st.set_page_config(layout="wide")
st.title("Own Your Data \n on your machine, in your browser\n", anchor=False)

pg = st.navigation(
    [st.Page(generate_charts.main, title="Charts", url_path="/"), st.Page(about.main, title="About", url_path="about")]
)

pg.run()
