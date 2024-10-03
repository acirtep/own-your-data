# own-your-data

This is an (experimental) in-browser application, based on:
1. [stlite](https://github.com/whitphx/stlite)
2. [streamlit](https://streamlit.io/)
3. [plotly](https://plotly.com/)
4. [duckdb](https://duckdb.org/)
5. [pyodide](https://pyodide.org/en/stable/)

The application is available at: https://acirtep.github.io/own-your-data/

## run it locally

Install Python 3.12 or greater

## with Pyodide
1. Run `python3 -m http.server`
2. Go to http://localhost:8000/, in your browser

## with Python
1. Install packages `poetry install`
2. Run `make local_run`


### Miscellaneous

#### Generate synthetic data
1. Run app locally and execute `make demo_csv`