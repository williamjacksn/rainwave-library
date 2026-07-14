import sqlite3


def connection_init(path: str) -> None:
    con = sqlite3.connect(path)
    con.execute("pragma journal_mode=wal")
    con.close()


def connection_get(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path, autocommit=False)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=5000")
    return con
