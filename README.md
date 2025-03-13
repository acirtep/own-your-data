# own-your-data

This is an (experimental) in-browser application, based on:
1. [stlite](https://github.com/whitphx/stlite)
2. [streamlit](https://streamlit.io/)
3. [plotly](https://plotly.com/)
4. [duckdb](https://duckdb.org/)
5. [pyodide](https://pyodide.org/en/stable/)

The application is available at: https://www.own-your-data.nl


## run it locally

Running the application locally, a directory `own-your-data` will be created automatically in your $home directory.

## with Pyodide
⚠️ Might not work on certain Safari/iOS systems.
1. Install Python 3.12 or greater
2. Run `python3 -m http.server`
3. Go to http://localhost:8000/playground.html, which will open the application in your browser

## with Python
1. Install Python 3.12 or greater
2. Install poetry
3. Install packages `poetry install`
4. Run `make local_run`

## as a desktop app
1. Install npm
2. Run `npm install`
3. Run `npm run dump`
4. Run `npm run serve`

### Miscellaneous

#### Generate synthetic data
1. Run app locally and execute `make demo_file`