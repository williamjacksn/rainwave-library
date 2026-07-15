import logging
import os
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


def setting_get(con: sqlite3.Connection, key: str) -> str | None:
    row = con.execute(
        "select value from settings where key = :key",
        {"key": key},
    ).fetchone()
    if row is None:
        return None
    return row["value"]


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


def _migration_2(con: sqlite3.Connection) -> None:
    environment_settings = {
        "BSKY_HANDLE": "bluesky/handle",
        "BSKY_PASSWORD": "bluesky/password",
        "DISCORD_GUILD_ID": "discord/guild-id",
        "DISCORD_ROLE_ID_STAFF": "discord/staff-role-id",
        "LIBRARY_ROOT": "library/root",
        "OPENID_CLIENT_ID": "openid/client-id",
        "OPENID_CLIENT_SECRET": "openid/client-secret",
        "RW_CNX": "rainwave/connection",
        "SCHEME": "app/url-scheme",
        "SECRET_KEY": "app/secret-key",
    }
    settings = [
        {"key": key, "value": value}
        for environment_name, key in environment_settings.items()
        if (value := os.getenv(environment_name)) is not None
    ]
    con.executemany(
        """
        insert into settings (key, value)
        values (:key, :value)
        on conflict (key) do nothing
        """,
        settings,
    )


MIGRATIONS = (_migration_1, _migration_2)


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
