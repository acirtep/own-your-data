import re
from pathlib import Path
from zipfile import ZipFile

import streamlit as st

from own_your_data.utils import add_timestamp_to_str
from own_your_data.utils import cleanup_db
from own_your_data.utils import gather_database_size
from own_your_data.utils import get_duckdb_conn
from own_your_data.utils import timeit


def clean_column_name(column_name: str) -> str:
    return " ".join(re.sub("[^A-Za-z0-9 ]+", " ", column_name).title().split())


def get_table_name(file_name: str) -> str:
    cleaned_table_name = "_".join(re.sub("[^A-Za-z0-9 ]+", " ", file_name).split())
    return f"file_{cleaned_table_name.lower()}"


@timeit
def get_unzipped_data(data_source, file_types):
    extract_dir = f"{str(Path.home())}/own-your-data/imports/unzipped"
    with ZipFile(data_source) as zip_files:
        zip_files.extractall(extract_dir)
    return [file for file in Path(extract_dir).iterdir() if file.is_file() and file.suffix.lower() in file_types]


@timeit
@gather_database_size
def import_uploaded_file(data_source, table_name, file_name):
    duckdb_conn = get_duckdb_conn()
    imported_data = duckdb_conn.read_csv(data_source)  # NOQA
    duckdb_conn.execute(f"create table {table_name} as select * from imported_data")

    duckdb_conn.execute(
        f"""
        insert into file_import_metadata
        (id, file_name, table_name, start_import_datetime)
            values
        (   -- TODO handle sequence in copy database
            (select max(id)  from file_import_metadata where table_name = '{table_name}_t') + 1,
            '{file_name}', '{table_name}_t', current_timestamp
        )
    """
    )


def get_auto_column_expressions(table_name) -> list[str]:
    # from timestamp to date
    # from date to year, month name, day name
    duckdb_conn = get_duckdb_conn()
    date_related_columns = duckdb_conn.execute(
        f"""
        select column_name,
            case when data_type like 'TIMESTAMP%' then true else false end is_timestamp
        from duckdb_columns a
        where a.table_name='{table_name}'
        and (a.data_type = 'DATE' or a.data_type like 'TIMESTAMP%')
        and column_name not like '% Date Auto'
        and not exists (
            select 1
            from duckdb_columns b
            where a.table_name = b.table_name
            and b.column_name like concat(a.column_name, ' % Auto')
        )
        """
    ).fetchall()

    auto_column_expressions = [
        f"""
                monthname("{column[0]}") as "{clean_column_name(column_name=column[0])} Month Name Auto",
                dayname("{column[0]}") as "{clean_column_name(column_name=column[0])} Day Name Auto",
                date_part('year', "{column[0]}") as "{clean_column_name(column_name=column[0])} Year Auto"
        """
        for column in date_related_columns
    ]
    auto_column_expressions.extend(
        [
            f""" "{column[0]}"::date as "{clean_column_name(column_name=column[0])} Date Auto" """
            for column in date_related_columns
            if column[1]
        ]
    )
    return auto_column_expressions


@timeit
@gather_database_size
def process_imported_data(table_name: str, add_auto_columns: bool = True):
    duckdb_conn = get_duckdb_conn()
    auto_column_expressions = get_auto_column_expressions(table_name=table_name) if add_auto_columns else None
    column_selection = [
        f'"{column[0]}" as "{" ".join(re.sub("[^A-Za-z0-9 ]+", " ", column[0]).title().split())}"'
        for column in duckdb_conn.execute(
            f"select column_name from duckdb_columns where table_name='{table_name}'"
        ).fetchall()
    ]
    if auto_column_expressions:
        column_selection.extend(auto_column_expressions)

    duckdb_conn.execute(
        f"""
        create table {table_name}_t as
        select {','.join(column_selection)}
        from {table_name} it
    """
    )

    duckdb_conn.execute(
        f"""
        update file_import_metadata
            set end_import_datetime = current_timestamp
        where table_name = '{table_name}_t'
        and id = (select max(id) from file_import_metadata where table_name = '{table_name}_t')
    """
    )

    duckdb_conn.execute(f"drop table {table_name}")


@timeit
def import_demo_file():
    table_name = get_table_name("demo_file.txt")
    cleanup_db(table_name=f"{table_name}_t")
    import_uploaded_file(
        data_source=f"{Path(__file__).parent.parent}/demo/demo_file.txt",
        table_name=table_name,
        file_name="demo_file.txt",
    )
    process_imported_data(table_name=table_name)


@gather_database_size
def copy_imported_database(file_name: str, original_file_name: str):
    duckdb_conn = get_duckdb_conn()

    # attach file as database
    duckdb_conn.sql("detach database if exists own_your_data_import")
    duckdb_conn.sql(f"attach '{file_name}' as own_your_data_import")

    # remove technical tables
    duckdb_conn.sql("drop table if exists own_your_data_import.file_import_metadata")
    duckdb_conn.sql("drop table if exists own_your_data_import.database_size_monitoring")
    duckdb_conn.sql("drop table if exists own_your_data_import.calendar_t")

    # rename common tables
    import_date_suffix = f"{add_timestamp_to_str(Path(original_file_name).stem)}"
    for unaccepted_char in [".", " "]:
        import_date_suffix = import_date_suffix.replace(unaccepted_char, "_")

    common_tables = duckdb_conn.sql(
        "select table_name from information_schema.tables group by 1 having count(*)>1"
    ).set_alias("duplicated_tbl")
    common_tables_import = (
        duckdb_conn.sql(
            "select table_name, table_type from information_schema.tables where table_catalog = 'own_your_data_import'"
        )
        .set_alias("imported_db")
        .join(common_tables, "imported_db.table_name = duplicated_tbl.table_name")
        .select("imported_db.table_name, imported_db.table_type")
        .fetchall()
    )

    try:
        for common_table in common_tables_import:
            object_type = common_table[1] if common_table[1] == "VIEW" else "table"
            if st.session_state.import_type == "overwrite":
                cleanup_db(f"own_your_data.{common_table[0]}", object_type)
            else:
                duckdb_conn.sql(
                    f"""alter {object_type} own_your_data_import.{common_table[0]}
                    rename to {common_table[0]}_{import_date_suffix}"""
                )

        # copy from imported database to current database and detach
        duckdb_conn.sql("copy from database own_your_data_import to own_your_data")
    except Exception as err:
        raise err
    finally:
        duckdb_conn.sql("detach database if exists own_your_data_import")
