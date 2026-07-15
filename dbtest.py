"""Connect to Rainwave's configured PostgreSQL database and run ad-hoc queries.

Reads the PostgreSQL connection string from the SQLite settings database, using
the same STORAGE_CNX / STATE_DIRECTORY configuration as the app. Run it with
the same environment file:

    uv run --env-file .local/.env dbtest.py "select * from r4_songs limit 5"

Omit the query argument to read SQL from stdin or enter an interactive prompt:

    uv run --env-file .local/.env dbtest.py
"""

import argparse
import os
import pathlib
import sys

import fort

import rainwave_library.models.rainwave
import rainwave_library.models.storage


def database_get() -> fort.PostgresDatabase:
    storage_dir = pathlib.Path(os.getenv("STATE_DIRECTORY") or ".local")
    storage_path = os.getenv(
        "STORAGE_CNX", str(storage_dir / "rainwave-library.db")
    )
    rainwave_library.models.storage.connection_init(storage_path)
    storage_cnx = rainwave_library.models.storage.connection_get(storage_path)
    try:
        rainwave_library.models.storage.migrate(storage_cnx)
        dsn = rainwave_library.models.storage.setting_get(
            storage_cnx, "rainwave/connection"
        )
    finally:
        storage_cnx.close()

    if not dsn:
        msg = "Missing required setting: rainwave/connection"
        raise RuntimeError(msg)
    return rainwave_library.models.rainwave.connection_get(dsn)


def run(
    db: fort.PostgresDatabase,
    sql: str,
    params: dict[str, object] | None = None,
) -> None:
    sql = sql.strip().rstrip(";")
    if not sql:
        return
    if not sql.lower().startswith("select"):
        print("error: only SELECT queries are allowed")
        return
    if ";" in sql:
        print("error: only a single statement is allowed")
        return
    rows = db.q(sql, params)
    if not rows:
        print("(no rows)")
        return
    columns = list(rows[0].keys())
    widths = {column: len(column) for column in columns}
    for row in rows:
        for column in columns:
            widths[column] = max(widths[column], len(str(row[column])))
    header = "  ".join(column.ljust(widths[column]) for column in columns)
    print(header)
    print("  ".join("-" * widths[column] for column in columns))
    for row in rows:
        print(
            "  ".join(str(row[column]).ljust(widths[column]) for column in columns)
        )
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Connect to Rainwave's configured database and run ad-hoc queries."
    )
    parser.add_argument(
        "sql",
        nargs="*",
        help="SQL to run. If omitted, read from stdin or start an interactive prompt.",
    )
    parser.add_argument(
        "--tables",
        action="store_true",
        help="List the tables in the public schema.",
    )
    parser.add_argument(
        "--describe",
        metavar="TABLE",
        help="Show the columns of TABLE.",
    )
    args = parser.parse_args()

    db = database_get()

    if args.tables:
        run(
            db,
            """
            select tablename
            from pg_tables
            where schemaname = 'public'
            order by tablename
            """,
        )
        return

    if args.describe:
        run(
            db,
            """
            select column_name, data_type, is_nullable
            from information_schema.columns
            where table_schema = 'public' and table_name = %(table)s
            order by ordinal_position
            """,
            {"table": args.describe},
        )
        return

    if args.sql:
        run(db, " ".join(args.sql))
        return

    if not sys.stdin.isatty():
        run(db, sys.stdin.read())
        return

    print("Connected. Enter a query (or 'quit' to exit).")
    while True:
        try:
            sql = input("sql> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if sql.strip().lower() in {"quit", "exit"}:
            break
        try:
            run(db, sql)
        except Exception as e:
            print(f"error: {e}")


if __name__ == "__main__":
    main()
