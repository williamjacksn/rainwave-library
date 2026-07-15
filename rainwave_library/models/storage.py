import logging
import os
import sqlite3

log = logging.getLogger(__name__)


def connection_init(path: str) -> None:
    con = sqlite3.connect(path)
    con.execute("pragma journal_mode=wal")
    con.close()


def connection_get(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path, autocommit=True)
    con.row_factory = sqlite3.Row
    con.execute("pragma busy_timeout=5000")
    con.execute("pragma foreign_keys=on")
    con.autocommit = False
    return con


def setting_get(con: sqlite3.Connection, key: str) -> str | None:
    row = con.execute(
        "select value from settings where key = :key",
        {"key": key},
    ).fetchone()
    if row is None:
        return None
    return row["value"]


def settings_get(con: sqlite3.Connection) -> list[tuple[str, str, bool]]:
    rows = con.execute(
        "select key, value, protected from settings order by key"
    ).fetchall()
    return [(row["key"], row["value"], bool(row["protected"])) for row in rows]


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


def _migration_3(con: sqlite3.Connection) -> None:
    con.execute(
        """
        alter table settings
        add column protected integer not null default 0
            check (protected in (0, 1))
        """
    )
    con.execute(
        """
        update settings
        set protected = 1
        where key in (
            'app/secret-key',
            'bluesky/password',
            'openid/client-secret',
            'rainwave/connection'
        )
        """
    )


def _migration_4(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create table suggestions (
            suggestion_id text primary key not null,
            title text not null,
            kind text not null default 'addition'
                check (kind in ('addition', 'removal', 'cleanup')),
            status text not null default 'new'
                check (
                    status in (
                        'new', 'claimed', 'fulfilled', 'declined', 'processed'
                    )
                ),
            archived integer not null default 0
                check (archived in (0, 1)),
            description text not null default '',
            requester_name text,
            requester_discord_id text,
            requested_at text,
            claimed_by_name text,
            claimed_by_discord_id text,
            claimed_at text,
            resolved_at text,
            resolution_notes text,
            sort_order real not null default 0,
            created_at text not null,
            updated_at text not null,
            trello_card_id text unique,
            trello_url text
        ) without rowid;

        create index suggestions_status_idx
            on suggestions (archived, status, sort_order);
        create index suggestions_claimed_by_idx
            on suggestions (claimed_by_discord_id, claimed_by_name);

        create table suggestion_channels (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            channel_id integer not null,
            is_primary integer not null default 0
                check (is_primary in (0, 1)),
            primary key (suggestion_id, channel_id)
        ) without rowid;

        create table suggestion_links (
            link_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            link_type text not null,
            url text not null,
            label text,
            sort_order real not null default 0,
            trello_attachment_id text unique,
            unique (suggestion_id, url)
        ) without rowid;

        create index suggestion_links_suggestion_idx
            on suggestion_links (suggestion_id, sort_order);

        create table suggestion_tags (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            tag text not null,
            primary key (suggestion_id, tag)
        ) without rowid;

        create table suggestion_activity (
            activity_id text primary key not null,
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            activity_type text not null,
            actor_name text,
            actor_discord_id text,
            body text,
            old_value text,
            new_value text,
            created_at text not null,
            trello_action_id text unique,
            trello_member_id text
        ) without rowid;

        create index suggestion_activity_suggestion_idx
            on suggestion_activity (suggestion_id, created_at);
        """
    )


MIGRATIONS = (_migration_1, _migration_2, _migration_3, _migration_4)


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
