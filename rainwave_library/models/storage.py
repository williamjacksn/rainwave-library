import logging
import os
import pathlib
import shutil
import sqlite3
import typing

log = logging.getLogger(__name__)


def suggestion_staging_files_get(
    library_root: pathlib.Path,
    suggestion_id: str,
) -> tuple[tuple[str, int], ...]:
    staging_root = (library_root / "staging").resolve()
    suggestion_root = (staging_root / suggestion_id).resolve()
    if suggestion_root == staging_root or not suggestion_root.is_relative_to(
        staging_root
    ):
        msg = "Invalid suggestion staging directory."
        raise ValueError(msg)
    if not suggestion_root.is_dir():
        return ()

    files = []
    for path in suggestion_root.rglob("*"):
        try:
            if not path.is_file():
                continue
            files.append(
                (
                    path.relative_to(suggestion_root).as_posix(),
                    path.stat().st_size,
                )
            )
        except OSError:
            continue
    return tuple(sorted(files, key=lambda file: file[0].casefold()))


def suggestion_staging_files_upload(
    library_root: pathlib.Path,
    suggestion_id: str,
    uploads: typing.Iterable[tuple[str, typing.IO[bytes]]],
) -> tuple[str, ...]:
    normalized_uploads = []
    for original_name, stream in uploads:
        filename = pathlib.PurePosixPath(original_name.replace("\\", "/")).name.strip()
        if (
            not filename
            or filename in {".", ".."}
            or any(ord(character) < 32 for character in filename)
        ):
            msg = "Every uploaded file must have a valid filename."
            raise ValueError(msg)
        if len(filename.encode()) > 255:
            msg = f"The filename {filename!r} is too long."
            raise ValueError(msg)
        normalized_uploads.append((filename, stream))
    if not normalized_uploads:
        msg = "Choose at least one file to upload."
        raise ValueError(msg)

    normalized_names = [filename.casefold() for filename, _ in normalized_uploads]
    if len(normalized_names) != len(set(normalized_names)):
        msg = "The upload contains duplicate filenames."
        raise ValueError(msg)

    staging_root = (library_root / "staging").resolve()
    suggestion_root = (staging_root / suggestion_id).resolve()
    if suggestion_root == staging_root or not suggestion_root.is_relative_to(
        staging_root
    ):
        msg = "Invalid suggestion staging directory."
        raise ValueError(msg)
    suggestion_root.mkdir(parents=True, exist_ok=True)

    destinations = [suggestion_root / filename for filename, _ in normalized_uploads]
    existing_names = {path.name.casefold() for path in suggestion_root.iterdir()}
    if any(
        destination.name.casefold() in existing_names for destination in destinations
    ):
        msg = "A file with that name already exists in the suggestion folder."
        raise ValueError(msg)

    created: list[pathlib.Path] = []
    try:
        for destination, (_, stream) in zip(
            destinations, normalized_uploads, strict=True
        ):
            with destination.open("xb") as target:
                created.append(destination)
                shutil.copyfileobj(stream, target)
    except Exception:
        for destination in created:
            destination.unlink(missing_ok=True)
        raise
    return tuple(destination.name for destination in destinations)


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


def setting_set(
    con: sqlite3.Connection,
    key: str,
    value: str,
    *,
    protected: bool = False,
) -> bool:
    key = key.strip()
    if not key:
        msg = "Setting key is required."
        raise ValueError(msg)
    if not value:
        msg = "Setting value is required."
        raise ValueError(msg)

    created = setting_get(con, key) is None
    try:
        con.execute(
            """
            insert into settings (key, value, protected)
            values (:key, :value, :protected)
            on conflict (key) do update set
                value = excluded.value,
                protected = max(settings.protected, excluded.protected)
            """,
            {
                "key": key,
                "value": value,
                "protected": int(protected),
            },
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    return created


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


def _migration_5(con: sqlite3.Connection) -> None:
    con.execute(
        """
        update suggestions
        set status = 'fulfilled'
        where status = 'processed'
        """
    )


def _migration_6(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create temp table _migration_6_suggestions as
            select * from suggestions;
        create temp table _migration_6_suggestion_channels as
            select * from suggestion_channels;
        create temp table _migration_6_suggestion_links as
            select * from suggestion_links;
        create temp table _migration_6_suggestion_tags as
            select * from suggestion_tags;
        create temp table _migration_6_suggestion_activity as
            select * from suggestion_activity;

        drop table suggestion_activity;
        drop table suggestion_tags;
        drop table suggestion_links;
        drop table suggestion_channels;
        drop table suggestions;

        create table suggestions (
            suggestion_id text primary key not null,
            title text not null,
            kind text not null default 'addition'
                check (kind in ('addition', 'removal', 'cleanup')),
            status text not null default 'new'
                check (
                    status in (
                        'new', 'claimed', 'accepted', 'uploaded', 'declined'
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

        insert into suggestions (
            suggestion_id,
            title,
            kind,
            status,
            archived,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            resolution_notes,
            sort_order,
            created_at,
            updated_at,
            trello_card_id,
            trello_url
        )
        select
            suggestion_id,
            title,
            kind,
            case
                when status in ('fulfilled', 'processed') then 'uploaded'
                else status
            end,
            archived,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            resolution_notes,
            sort_order,
            created_at,
            updated_at,
            trello_card_id,
            trello_url
        from _migration_6_suggestions;

        create table suggestion_channels (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            channel_id integer not null,
            is_primary integer not null default 0
                check (is_primary in (0, 1)),
            primary key (suggestion_id, channel_id)
        ) without rowid;

        insert into suggestion_channels (suggestion_id, channel_id, is_primary)
        select suggestion_id, channel_id, is_primary
        from _migration_6_suggestion_channels;

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

        insert into suggestion_links (
            link_id,
            suggestion_id,
            link_type,
            url,
            label,
            sort_order,
            trello_attachment_id
        )
        select
            link_id,
            suggestion_id,
            link_type,
            url,
            label,
            sort_order,
            trello_attachment_id
        from _migration_6_suggestion_links;

        create table suggestion_tags (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            tag text not null,
            primary key (suggestion_id, tag)
        ) without rowid;

        insert into suggestion_tags (suggestion_id, tag)
        select suggestion_id, tag
        from _migration_6_suggestion_tags;

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

        insert into suggestion_activity (
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_action_id,
            trello_member_id
        )
        select
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_action_id,
            trello_member_id
        from _migration_6_suggestion_activity;

        drop table _migration_6_suggestion_activity;
        drop table _migration_6_suggestion_tags;
        drop table _migration_6_suggestion_links;
        drop table _migration_6_suggestion_channels;
        drop table _migration_6_suggestions;
        """
    )


def _migration_7(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        update suggestion_activity
        set activity_type = 'updated-suggested-by-name'
        where activity_type = 'updated-requester-name';

        update suggestion_activity
        set activity_type = 'updated-suggested-by-discord-id'
        where activity_type = 'updated-requester-discord-id';

        update suggestion_activity
        set activity_type = 'updated-suggested-at'
        where activity_type = 'updated-requested-at';
        """
    )


def _migration_8(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        create temp table _migration_8_suggestions as
            select * from suggestions;
        create temp table _migration_8_suggestion_channels as
            select * from suggestion_channels;
        create temp table _migration_8_suggestion_links as
            select * from suggestion_links;
        create temp table _migration_8_suggestion_tags as
            select * from suggestion_tags;
        create temp table _migration_8_suggestion_activity as
            select * from suggestion_activity;

        drop table suggestion_activity;
        drop table suggestion_tags;
        drop table suggestion_links;
        drop table suggestion_channels;
        drop table suggestions;

        create table suggestions (
            suggestion_id text primary key not null,
            title text not null,
            kind text not null default 'new-album'
                check (
                    kind in (
                        'new-album',
                        'add-to-existing-album',
                        'metadata-update',
                        'removal'
                    )
                ),
            status text not null default 'new'
                check (
                    status in (
                        'new', 'claimed', 'accepted', 'uploaded', 'declined'
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

        insert into suggestions (
            suggestion_id,
            title,
            kind,
            status,
            archived,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            resolution_notes,
            sort_order,
            created_at,
            updated_at,
            trello_card_id,
            trello_url
        )
        select
            suggestion_id,
            title,
            case kind
                when 'addition' then 'new-album'
                when 'cleanup' then 'metadata-update'
                when 'removal' then 'removal'
                else 'new-album'
            end,
            status,
            archived,
            description,
            requester_name,
            requester_discord_id,
            requested_at,
            claimed_by_name,
            claimed_by_discord_id,
            claimed_at,
            resolved_at,
            resolution_notes,
            sort_order,
            created_at,
            updated_at,
            trello_card_id,
            trello_url
        from _migration_8_suggestions;

        create table suggestion_channels (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            channel_id integer not null,
            is_primary integer not null default 0
                check (is_primary in (0, 1)),
            primary key (suggestion_id, channel_id)
        ) without rowid;

        insert into suggestion_channels (suggestion_id, channel_id, is_primary)
        select suggestion_id, channel_id, is_primary
        from _migration_8_suggestion_channels;

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

        insert into suggestion_links (
            link_id,
            suggestion_id,
            link_type,
            url,
            label,
            sort_order,
            trello_attachment_id
        )
        select
            link_id,
            suggestion_id,
            link_type,
            url,
            label,
            sort_order,
            trello_attachment_id
        from _migration_8_suggestion_links;

        create table suggestion_tags (
            suggestion_id text not null
                references suggestions (suggestion_id) on delete cascade,
            tag text not null,
            primary key (suggestion_id, tag)
        ) without rowid;

        insert into suggestion_tags (suggestion_id, tag)
        select suggestion_id, tag
        from _migration_8_suggestion_tags;

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

        insert into suggestion_activity (
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_action_id,
            trello_member_id
        )
        select
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at,
            trello_action_id,
            trello_member_id
        from _migration_8_suggestion_activity;

        drop table _migration_8_suggestion_activity;
        drop table _migration_8_suggestion_tags;
        drop table _migration_8_suggestion_links;
        drop table _migration_8_suggestion_channels;
        drop table _migration_8_suggestions;
        """
    )


def _migration_9(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        update suggestion_activity
        set
            old_value = case old_value
                when 'addition' then 'new-album'
                when 'cleanup' then 'metadata-update'
                else old_value
            end,
            new_value = case new_value
                when 'addition' then 'new-album'
                when 'cleanup' then 'metadata-update'
                else new_value
            end
        where activity_type = 'updated-kind';
        """
    )


MIGRATIONS = (
    _migration_1,
    _migration_2,
    _migration_3,
    _migration_4,
    _migration_5,
    _migration_6,
    _migration_7,
    _migration_8,
    _migration_9,
)


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
