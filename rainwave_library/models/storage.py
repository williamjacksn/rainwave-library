import logging
import sqlite3

log = logging.getLogger(__name__)


def connection_init(path: str) -> None:
    con = sqlite3.connect(path)
    con.execute("pragma journal_mode=wal")
    con.close()


def connection_get(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path, autocommit=False)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=5000")
    return con


def user_version_get(con: sqlite3.Connection) -> int:
    return con.execute("pragma user_version").fetchone()[0]


def user_version_set(con: sqlite3.Connection, version: int) -> None:
    if not 0 <= version <= 2_147_483_647:
        msg = "SQLite user_version must be a nonnegative 32-bit signed integer"
        raise ValueError(msg)
    con.execute(f"pragma user_version={version}")


def _migration_1(con: sqlite3.Connection) -> None:
    con.execute(
        """
        create table settings (
            key text primary key not null,
            value text not null
        )
        """
    )


MIGRATIONS = (_migration_1,)


def migrate(con: sqlite3.Connection) -> None:
    current_version = user_version_get(con)
    latest_version = len(MIGRATIONS)
    if not 0 <= current_version <= latest_version:
        msg = (
            f"Unsupported database version {current_version}; "
            f"latest supported version is {latest_version}"
        )
        raise RuntimeError(msg)

    try:
        for version, migration in enumerate(MIGRATIONS, start=1):
            if version <= current_version:
                continue
            log.info("Running database migration %d", version)
            migration(con)
            user_version_set(con, version)
        con.commit()
    except Exception:
        con.rollback()
        raise
