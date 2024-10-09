import streamlit as st


def main():

    st.subheader(
        "Do you track your personal data on your computer or do you have it stored in a csv?",
        anchor=False,
        divider=True,
    )

    st.subheader(
        "You can visualize it with Plotly, by importing it with duckdb in your browser", anchor=False, divider=True
    )

    st.markdown(
        """
        <a href="https://github.com/acirtep/own-your-data" target="_blank">
            <img
                src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
                width="15"
                style="vertical-align: middle;
                margin-left: 10px;"
            >
        </a>
        Use your data in your web browser, powered by Pyodide through stlite, streamlit, plotly and duckdb
        """,
        unsafe_allow_html=True,
    )
