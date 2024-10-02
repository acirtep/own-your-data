import streamlit as st

st.title("Own Your Data \n on your machine in your browser\n")

st.subheader(
    "Do you track your personal data on your computer or do you have it stored in a csv?", anchor=False, divider=True
)

st.subheader(
    "You can visualize it with Plotly, by importing it with duckdb in your browser", anchor=False, divider=True
)

st.text("Using Streamlit in your web browser, powered by Pyodide through stlite")
