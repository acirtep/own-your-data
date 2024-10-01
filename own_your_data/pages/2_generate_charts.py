import duckdb
import streamlit as st

with st.sidebar.expander("Data source"):
    data_source = st.file_uploader("Upload a file", type=["csv"], help="The data is saved in memory only!")
    separator = st.radio("separator", (";", ",", "|"), index=0, horizontal=True, key="upload-csv-sep")
    header_position_in_file = st.text_input("What's the header position?", value=1)

height = st.sidebar.slider("height", min_value=400, max_value=4000, step=50)

width = st.sidebar.slider("width", min_value=600, max_value=3000, step=50, value=1200)

orientation = st.sidebar.radio("orientation", ("h", "v"), help="h=horizontal, v=vertical, default h", horizontal=True)

arrangement = st.sidebar.radio(
    "arrangement",
    ("snap", "perpendicular", "freeform", "fixed"),
    help="""Default: "snap"
    If value is `snap` (the default), the node arrangement is assisted by automatic snapping of elements to \
    preserve space between nodes specified via `nodepad`. If value is `perpendicular`, the nodes can only move \
    along a line perpendicular to the flow. If value is `freeform`, the nodes can freely move on the plane. \
    If value is `fixed`, the nodes are stationary.""",
)

if data_source:
    session_duckdb_conn = duckdb.connect()
    df = session_duckdb_conn.read_csv(data_source).df()
    st.dataframe(df)
