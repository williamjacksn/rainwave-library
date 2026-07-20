import datetime
import logging
import re
import secrets
import sqlite3
import typing
import urllib.parse
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

_TRELLO_API = "https://api.trello.com/1"
_CHANNEL_LABELS = {
    "game": 1,
    "oc remix": 2,
    "ocremix": 2,
    "covers": 3,
    "chiptune": 4,
    "chill": 6,
}
_LIST_CHANNELS = {
    "Fresh Game": 1,
    "Fresh OC ReMix": 2,
    "Fresh Covers": 3,
    "Fresh Chiptune": 4,
    "Fresh Chill": 6,
}
_URL_PATTERN = re.compile(r'https?://[^\s\]>)"]+')
_REQUESTER_PATTERNS = (
    re.compile(
        r"(?im)^\s*(?:request(?:ed)?|suggested)\s+by\s+(.+?)"
        r"(?=\s+(?:on|through)\b|[.\n]|$)"
    ),
    re.compile(r"(?im)^\s*(?:requested|suggested)\s+on\s+\S+\s+by\s+([^\.\n]+)"),
)
_DATE_PATTERN = re.compile(r"\b(\d{1,4})[/-](\d{1,2})[/-](\d{2,4})\b")


@dataclass(frozen=True)
class TrelloImportResult:
    suggestions: int
    channels: int
    links: int
    tags: int
    activities: int
    skipped: int


@dataclass(frozen=True)
class Suggestion:
    colspan: typing.ClassVar[int] = 7
    kinds: typing.ClassVar[tuple[str, ...]] = ("addition", "removal", "cleanup")
    sort_fields: typing.ClassVar[tuple[tuple[str, str], ...]] = (
        ("status", "Status"),
        ("title", "Suggestion"),
        ("requester_name", "Suggested by"),
        ("requested_at", "Suggested at"),
        ("claimed_by_name", "Claimed by"),
    )
    statuses: typing.ClassVar[tuple[str, ...]] = (
        "new",
        "claimed",
        "accepted",
        "uploaded",
        "declined",
    )

    id: str
    title: str
    kind: str
    status: str
    description: str
    requester_name: str | None
    requester_discord_id: str | None
    requested_at: str | None
    claimed_by_name: str | None
    claimed_by_discord_id: str | None
    channel_ids: tuple[int, ...]
    tags: tuple[str, ...]


@dataclass(frozen=True)
class SuggestionLink:
    id: str
    type: str
    url: str
    label: str | None
    sort_order: float
    trello_attachment_id: str | None


@dataclass(frozen=True)
class SuggestionActivity:
    id: str
    type: str
    actor_name: str | None
    actor_discord_id: str | None
    body: str | None
    old_value: str | None
    new_value: str | None
    created_at: str
    trello_action_id: str | None
    trello_member_id: str | None


@dataclass(frozen=True)
class SuggestionDetail(Suggestion):
    primary_channel_id: int | None
    claimed_at: str | None
    resolved_at: str | None
    resolution_notes: str | None
    sort_order: float
    created_at: str
    updated_at: str
    trello_card_id: str | None
    trello_url: str | None
    links: tuple[SuggestionLink, ...]
    activities: tuple[SuggestionActivity, ...]


@dataclass(frozen=True)
class _ListInfo:
    kind: str = "addition"
    status: str = "new"
    claimed_by_name: str | None = None
    primary_channel_id: int | None = None
    skip: bool = False
    known: bool = True


def id_new() -> str:
    return secrets.token_urlsafe(16)


def _activity_insert(
    con: sqlite3.Connection,
    suggestion_id: str,
    *,
    activity_type: str,
    actor_name: str | None = None,
    actor_discord_id: str | None = None,
    body: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    con.execute(
        """
        insert into suggestion_activity (
            activity_id,
            suggestion_id,
            activity_type,
            actor_name,
            actor_discord_id,
            body,
            old_value,
            new_value,
            created_at
        ) values (
            :activity_id,
            :suggestion_id,
            :activity_type,
            :actor_name,
            :actor_discord_id,
            :body,
            :old_value,
            :new_value,
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        )
        """,
        {
            "activity_id": id_new(),
            "suggestion_id": suggestion_id,
            "activity_type": activity_type,
            "actor_name": actor_name,
            "actor_discord_id": actor_discord_id,
            "body": body,
            "old_value": old_value,
            "new_value": new_value,
        },
    )


def _suggestion_from_row(row: sqlite3.Row) -> Suggestion:
    return Suggestion(
        id=row["suggestion_id"],
        title=row["title"],
        kind=row["kind"],
        status=row["status"],
        description=row["description"],
        requester_name=row["requester_name"],
        requester_discord_id=row["requester_discord_id"],
        requested_at=row["requested_at"],
        claimed_by_name=row["claimed_by_name"],
        claimed_by_discord_id=row["claimed_by_discord_id"],
        channel_ids=tuple(
            sorted(
                int(channel_id)
                for channel_id in (row["channel_ids"] or "").split(",")
                if channel_id
            )
        ),
        tags=tuple(sorted((row["tags"] or "").split("\x1f"), key=str.casefold))
        if row["tags"]
        else (),
    )


def suggestions_get(
    con: sqlite3.Connection,
    query: str | None,
    statuses: typing.Iterable[str] | None,
    page: int,
    requester_discord_id: str | None = None,
    claimed_by_discord_id: str | None = None,
    sort_col: str = "requested_at",
    sort_dir: str = "desc",
    claimed_by_names: typing.Iterable[str] | None = None,
    channel_ids: typing.Iterable[int] | None = None,
) -> list[Suggestion]:
    query = query.strip() if query else None
    valid_statuses = tuple(
        dict.fromkeys(
            status for status in statuses or () if status in Suggestion.statuses
        )
    )
    status_parameters: list[str | None] = [*valid_statuses]
    status_parameters.extend([None] * (len(Suggestion.statuses) - len(valid_statuses)))
    valid_channel_ids = tuple(
        dict.fromkeys(
            channel_id
            for channel_id in channel_ids or ()
            if channel_id in {1, 2, 3, 4, 6}
        )
    )
    channel_parameters: list[int | None] = [*valid_channel_ids]
    channel_parameters.extend([None] * (5 - len(valid_channel_ids)))
    claimed_by_filters = tuple(name.strip() for name in claimed_by_names or ())
    include_unclaimed = "" in claimed_by_filters
    valid_claimed_by_names = tuple(
        dict.fromkeys(name for name in claimed_by_filters if name)
    )
    claimed_by_parameters = {
        f"claimed_by_name_{index}": name
        for index, name in enumerate(valid_claimed_by_names)
    }
    claimed_by_conditions = []
    if claimed_by_parameters:
        placeholders = ", ".join(f":{name}" for name in claimed_by_parameters)
        claimed_by_conditions.append(
            f"s.claimed_by_name collate nocase in ({placeholders})"
        )
    if include_unclaimed:
        claimed_by_conditions.append("nullif(trim(s.claimed_by_name), '') is null")
    claimed_by_clause = (
        f"and ({' or '.join(claimed_by_conditions)})" if claimed_by_conditions else ""
    )
    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"
    sort_expressions = {
        "status": (
            """
            case s.status
                when 'new' then 1
                when 'claimed' then 2
                when 'accepted' then 3
                when 'uploaded' then 4
                when 'declined' then 5
            end
            """,
            "s.sort_order",
            "s.title collate nocase",
        ),
        "title": ("s.title collate nocase",),
        "requester_name": (
            "s.requester_name collate nocase",
            "s.title collate nocase",
        ),
        "requested_at": ("s.requested_at", "s.title collate nocase"),
        "claimed_by_name": (
            "s.claimed_by_name collate nocase",
            "s.title collate nocase",
        ),
    }
    expressions = sort_expressions.get(sort_col, sort_expressions["requested_at"])
    sort_clause = ", ".join(
        f"{expression.strip()} {sort_dir}" for expression in expressions
    )
    page = max(page, 1)
    sql = f"""
        select
            s.suggestion_id,
            s.title,
            s.kind,
            s.status,
            s.description,
            s.requester_name,
            s.requester_discord_id,
            s.requested_at,
            s.claimed_by_name,
            s.claimed_by_discord_id,
            (
                select group_concat(channel_id, ',')
                from suggestion_channels sc
                where sc.suggestion_id = s.suggestion_id
            ) channel_ids,
            (
                select group_concat(tag, char(31))
                from suggestion_tags st
                where st.suggestion_id = s.suggestion_id
            ) tags
        from suggestions s
        where (
                :status_0 is null
                or s.status in (
                    :status_0, :status_1, :status_2, :status_3, :status_4
                )
            )
            and (
                :requester_discord_id is null
                or s.requester_discord_id = :requester_discord_id
            )
            and (
                :claimed_by_discord_id is null
                or s.claimed_by_discord_id = :claimed_by_discord_id
            )
            {claimed_by_clause}
            and (
                :channel_0 is null
                or exists (
                    select 1
                    from suggestion_channels filtered_channel
                    where filtered_channel.suggestion_id = s.suggestion_id
                        and filtered_channel.channel_id in (
                            :channel_0,
                            :channel_1,
                            :channel_2,
                            :channel_3,
                            :channel_4
                        )
                )
            )
            and (
                :query is null
                or s.title like :query
                or s.description like :query
                or coalesce(s.requester_name, '') like :query
                or coalesce(s.claimed_by_name, '') like :query
            )
        order by
            {sort_clause},
            s.suggestion_id
        limit 101 offset :offset
        """  # noqa: S608
    rows = con.execute(
        sql,
        {
            "channel_0": channel_parameters[0],
            "channel_1": channel_parameters[1],
            "channel_2": channel_parameters[2],
            "channel_3": channel_parameters[3],
            "channel_4": channel_parameters[4],
            "claimed_by_discord_id": claimed_by_discord_id,
            "offset": 100 * (page - 1),
            "query": f"%{query}%" if query else None,
            "requester_discord_id": requester_discord_id,
            "status_0": status_parameters[0],
            "status_1": status_parameters[1],
            "status_2": status_parameters[2],
            "status_3": status_parameters[3],
            "status_4": status_parameters[4],
            **claimed_by_parameters,
        },
    ).fetchall()
    return [_suggestion_from_row(row) for row in rows]


def suggestion_claimants_get(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        """
        select min(claimed_by_name) claimed_by_name
        from suggestions
        where nullif(trim(claimed_by_name), '') is not null
        group by claimed_by_name collate nocase
        order by claimed_by_name collate nocase
        """
    ).fetchall()
    return [str(row["claimed_by_name"]) for row in rows]


def suggestion_counts_by_requester(
    con: sqlite3.Connection,
    requester_discord_id: str | None,
) -> tuple[int, int]:
    if not requester_discord_id:
        return 0, 0
    row = con.execute(
        """
        select
            count(*) filter (
                where status in ('new', 'claimed', 'accepted')
            ) active_count,
            count(*) filter (
                where status in ('uploaded', 'declined')
            ) complete_count
        from suggestions
        where requester_discord_id = ?
        """,
        (requester_discord_id,),
    ).fetchone()
    return int(row["active_count"]), int(row["complete_count"])


def suggestion_user_name_get(
    con: sqlite3.Connection,
    discord_user_id: str,
) -> str | None:
    row = con.execute(
        """
        select name
        from (
            select requester_name name, updated_at
            from suggestions
            where requester_discord_id = :discord_user_id

            union all

            select claimed_by_name name, updated_at
            from suggestions
            where claimed_by_discord_id = :discord_user_id
        ) names
        where nullif(trim(name), '') is not null
        order by updated_at desc
        limit 1
        """,
        {"discord_user_id": discord_user_id},
    ).fetchone()
    return str(row["name"]) if row is not None else None


def suggestion_get(
    con: sqlite3.Connection, suggestion_id: str
) -> SuggestionDetail | None:
    row = con.execute(
        """
        select
            s.*,
            (
                select group_concat(channel_id, ',')
                from suggestion_channels sc
                where sc.suggestion_id = s.suggestion_id
            ) channel_ids,
            (
                select group_concat(tag, char(31))
                from suggestion_tags st
                where st.suggestion_id = s.suggestion_id
            ) tags,
            (
                select channel_id
                from suggestion_channels sc
                where sc.suggestion_id = s.suggestion_id and sc.is_primary
                order by channel_id
                limit 1
            ) primary_channel_id
        from suggestions s
        where s.suggestion_id = ?
        """,
        (suggestion_id,),
    ).fetchone()
    if row is None:
        return None

    suggestion = _suggestion_from_row(row)
    links = tuple(
        SuggestionLink(
            id=link["link_id"],
            type=link["link_type"],
            url=link["url"],
            label=link["label"],
            sort_order=float(link["sort_order"]),
            trello_attachment_id=link["trello_attachment_id"],
        )
        for link in con.execute(
            """
            select *
            from suggestion_links
            where suggestion_id = ?
            order by sort_order, link_id
            """,
            (suggestion_id,),
        ).fetchall()
    )
    activities = tuple(
        SuggestionActivity(
            id=activity["activity_id"],
            type=activity["activity_type"],
            actor_name=activity["actor_name"],
            actor_discord_id=activity["actor_discord_id"],
            body=activity["body"],
            old_value=activity["old_value"],
            new_value=activity["new_value"],
            created_at=activity["created_at"],
            trello_action_id=activity["trello_action_id"],
            trello_member_id=activity["trello_member_id"],
        )
        for activity in con.execute(
            """
            select *
            from suggestion_activity
            where suggestion_id = ?
            order by created_at, activity_id
            """,
            (suggestion_id,),
        ).fetchall()
    )
    return SuggestionDetail(
        id=suggestion.id,
        title=suggestion.title,
        kind=suggestion.kind,
        status=suggestion.status,
        description=suggestion.description,
        requester_name=suggestion.requester_name,
        requested_at=suggestion.requested_at,
        claimed_by_name=suggestion.claimed_by_name,
        channel_ids=suggestion.channel_ids,
        tags=suggestion.tags,
        primary_channel_id=row["primary_channel_id"],
        requester_discord_id=row["requester_discord_id"],
        claimed_by_discord_id=row["claimed_by_discord_id"],
        claimed_at=row["claimed_at"],
        resolved_at=row["resolved_at"],
        resolution_notes=row["resolution_notes"],
        sort_order=float(row["sort_order"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        trello_card_id=row["trello_card_id"],
        trello_url=row["trello_url"],
        links=links,
        activities=activities,
    )


def suggestion_create(
    con: sqlite3.Connection,
    *,
    title: str,
    description: str,
    channel_id: int,
    requester_name: str | None,
    requester_discord_id: str | None,
    links: typing.Iterable[tuple[str, str]] = (),
) -> str:
    title = title.strip()
    if not title:
        msg = "Suggestion title is required."
        raise ValueError(msg)
    if channel_id not in {1, 2, 3, 4, 6}:
        msg = "A valid Rainwave channel is required."
        raise ValueError(msg)

    suggestion_id = id_new()
    try:
        con.execute(
            """
            insert into suggestions (
                suggestion_id,
                title,
                description,
                requester_name,
                requester_discord_id,
                requested_at,
                created_at,
                updated_at
            ) values (
                :suggestion_id,
                :title,
                :description,
                :requester_name,
                :requester_discord_id,
                strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            )
            """,
            {
                "suggestion_id": suggestion_id,
                "title": title,
                "description": description.strip(),
                "requester_name": requester_name,
                "requester_discord_id": requester_discord_id,
            },
        )
        con.execute(
            """
            insert into suggestion_channels (suggestion_id, channel_id, is_primary)
            values (?, ?, 1)
            """,
            (suggestion_id, channel_id),
        )
        for sort_order, (url, label) in enumerate(links):
            url = url.strip()
            if not url:
                continue
            con.execute(
                """
                insert into suggestion_links (
                    link_id, suggestion_id, link_type, url, label, sort_order
                ) values (?, ?, ?, ?, ?, ?)
                on conflict (suggestion_id, url) do nothing
                """,
                (
                    id_new(),
                    suggestion_id,
                    _link_type_get(url),
                    url,
                    label.strip() or None,
                    sort_order,
                ),
            )
        _activity_insert(
            con,
            suggestion_id,
            activity_type="created",
            actor_name=requester_name,
            actor_discord_id=requester_discord_id,
        )
        con.commit()
    except Exception:
        con.rollback()
        raise

    log.info("Created native suggestion %s", suggestion_id)
    return suggestion_id


def suggestion_claim(
    con: sqlite3.Connection,
    suggestion_id: str,
    claimed_by_name: str,
    claimed_by_discord_id: str,
) -> bool:
    claimed_by_name = claimed_by_name.strip()
    claimed_by_discord_id = claimed_by_discord_id.strip()
    if not claimed_by_name or not claimed_by_discord_id:
        msg = "A Discord display name and user ID are required to claim a suggestion."
        raise ValueError(msg)

    try:
        cursor = con.execute(
            """
            update suggestions
            set
                status = 'claimed',
                claimed_by_name = :claimed_by_name,
                claimed_by_discord_id = :claimed_by_discord_id,
                claimed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            where suggestion_id = :suggestion_id
                and status = 'new'
                and nullif(trim(claimed_by_name), '') is null
                and nullif(trim(claimed_by_discord_id), '') is null
            """,
            {
                "suggestion_id": suggestion_id,
                "claimed_by_name": claimed_by_name,
                "claimed_by_discord_id": claimed_by_discord_id,
            },
        )
        claimed = cursor.rowcount == 1
        if claimed:
            con.commit()
        else:
            con.rollback()
    except Exception:
        con.rollback()
        raise

    if claimed:
        log.info("Suggestion %s claimed by %s", suggestion_id, claimed_by_name)
    return claimed


def suggestion_release(
    con: sqlite3.Connection,
    suggestion_id: str,
    claimed_by_discord_id: str,
) -> bool:
    claimed_by_discord_id = claimed_by_discord_id.strip()
    if not claimed_by_discord_id:
        msg = "A Discord user ID is required to release a suggestion claim."
        raise ValueError(msg)

    try:
        cursor = con.execute(
            """
            update suggestions
            set
                status = 'new',
                claimed_by_name = null,
                claimed_by_discord_id = null,
                claimed_at = null,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            where suggestion_id = :suggestion_id
                and status = 'claimed'
                and claimed_by_discord_id = :claimed_by_discord_id
            """,
            {
                "suggestion_id": suggestion_id,
                "claimed_by_discord_id": claimed_by_discord_id,
            },
        )
        released = cursor.rowcount == 1
        if released:
            con.commit()
        else:
            con.rollback()
    except Exception:
        con.rollback()
        raise

    if released:
        log.info(
            "Suggestion %s claim released by Discord user %s",
            suggestion_id,
            claimed_by_discord_id,
        )
    return released


def suggestion_update(
    con: sqlite3.Connection,
    suggestion_id: str,
    *,
    title: str,
    kind: str,
    status: str,
    description: str,
    requester_name: str | None,
    requester_discord_id: str | None,
    requested_at: str | None,
    resolved_at: str | None,
    resolution_notes: str | None,
    channel_ids: typing.Iterable[int],
    primary_channel_id: int | None,
    actor_name: str | None = None,
    actor_discord_id: str | None = None,
) -> bool:
    title = title.strip()
    if not title:
        msg = "Suggestion title is required."
        raise ValueError(msg)
    if kind not in Suggestion.kinds:
        msg = "Invalid suggestion kind."
        raise ValueError(msg)
    if status not in Suggestion.statuses:
        msg = "Invalid suggestion status."
        raise ValueError(msg)
    normalized_channel_ids = set(channel_ids)
    if any(channel_id not in range(1, 7) for channel_id in normalized_channel_ids):
        msg = "Invalid Rainwave channel."
        raise ValueError(msg)
    if primary_channel_id is not None:
        if primary_channel_id not in range(1, 7):
            msg = "Invalid primary Rainwave channel."
            raise ValueError(msg)
        normalized_channel_ids.add(primary_channel_id)
    try:
        existing = con.execute(
            """
            select
                title,
                kind,
                status,
                description,
                requester_name,
                requester_discord_id,
                requested_at,
                resolved_at,
                resolution_notes
            from suggestions
            where suggestion_id = ?
            """,
            (suggestion_id,),
        ).fetchone()
        if existing is None:
            con.rollback()
            return False

        cursor = con.execute(
            """
            update suggestions
            set
                title = :title,
                kind = :kind,
                status = :status,
                description = :description,
                requester_name = :requester_name,
                requester_discord_id = :requester_discord_id,
                requested_at = :requested_at,
                resolved_at = :resolved_at,
                resolution_notes = :resolution_notes,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            where suggestion_id = :suggestion_id
            """,
            {
                "suggestion_id": suggestion_id,
                "title": title,
                "kind": kind,
                "status": status,
                "description": description,
                "requester_name": requester_name,
                "requester_discord_id": requester_discord_id,
                "requested_at": requested_at,
                "resolved_at": resolved_at,
                "resolution_notes": resolution_notes,
            },
        )
        if cursor.rowcount == 0:
            con.rollback()
            return False

        changes: tuple[tuple[str, str | None, str | None], ...] = (
            ("title", existing["title"], title),
            ("kind", existing["kind"], kind),
            ("status", existing["status"], status),
            ("description", existing["description"], description),
            ("suggested-by-name", existing["requester_name"], requester_name),
            (
                "suggested-by-discord-id",
                existing["requester_discord_id"],
                requester_discord_id,
            ),
            ("suggested-at", existing["requested_at"], requested_at),
            ("resolved-at", existing["resolved_at"], resolved_at),
            (
                "resolution-notes",
                existing["resolution_notes"],
                resolution_notes,
            ),
        )
        for slug, old_value, new_value in changes:
            if (old_value or None) == (new_value or None):
                continue
            _activity_insert(
                con,
                suggestion_id,
                activity_type=f"updated-{slug}",
                actor_name=actor_name,
                actor_discord_id=actor_discord_id,
                old_value=old_value,
                new_value=new_value,
            )

        con.execute(
            "delete from suggestion_channels where suggestion_id = ?",
            (suggestion_id,),
        )
        con.executemany(
            """
            insert into suggestion_channels (suggestion_id, channel_id, is_primary)
            values (?, ?, ?)
            """,
            (
                (
                    suggestion_id,
                    channel_id,
                    int(channel_id == primary_channel_id),
                )
                for channel_id in sorted(normalized_channel_ids)
            ),
        )
        con.commit()
    except Exception:
        con.rollback()
        raise

    log.info("Updated suggestion %s", suggestion_id)
    return True


def _json_list(
    client: httpx.Client,
    url: str,
    params: dict[str, str | int] | None = None,
) -> list[dict[str, typing.Any]]:
    response = client.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        msg = f"Expected a JSON list from {url}"
        raise ValueError(msg)
    return typing.cast(list[dict[str, typing.Any]], data)


def _comments_get(client: httpx.Client, board_url: str) -> list[dict[str, typing.Any]]:
    comments: list[dict[str, typing.Any]] = []
    before = None
    while True:
        params: dict[str, str | int] = {
            "filter": "commentCard",
            "limit": 1000,
        }
        if before is not None:
            params["before"] = before
        page = _json_list(client, f"{board_url}/actions", params)
        comments.extend(page)
        if len(page) < 1000:
            break
        next_before = str(page[-1].get("id") or "")
        if not next_before or next_before == before:
            break
        before = next_before
    return comments


def _list_info(name: str) -> _ListInfo:
    if name == "Suggestion Guidelines":
        return _ListInfo(skip=True)
    if name == "Removal Suggestions":
        return _ListInfo(kind="removal")
    if name in _LIST_CHANNELS:
        return _ListInfo(primary_channel_id=_LIST_CHANNELS[name])
    if name.endswith(" - Claimed"):
        return _ListInfo(
            status="claimed", claimed_by_name=name.removesuffix(" - Claimed")
        )
    if name == "Fulfilled":
        return _ListInfo(status="uploaded")
    if name == "Declined":
        return _ListInfo(status="declined")
    if name == "Processed for Chill":
        return _ListInfo(status="uploaded", primary_channel_id=6)
    return _ListInfo(known=False)


def _requester_name_get(description: str) -> str | None:
    for pattern in _REQUESTER_PATTERNS:
        match = pattern.search(description)
        if match is not None:
            name = match.group(1).strip()
            if name and len(name) <= 100:
                return name
    return None


def _requested_at_get(description: str) -> str | None:
    match = _DATE_PATTERN.search(description)
    if match is None:
        return None
    first, second, third = map(int, match.groups())
    try:
        if first >= 1000:
            requested = datetime.date(first, second, third)
        else:
            year = third + 2000 if third < 100 else third
            requested = datetime.date(year, first, second)
    except ValueError:
        return None
    return requested.isoformat()


def _created_at_get(card_id: str, updated_at: str) -> str:
    try:
        timestamp = int(card_id[:8], 16)
    except ValueError:
        return updated_at
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC).isoformat()


def _link_type_get(url: str) -> str:
    hostname = (urllib.parse.urlparse(url).hostname or "").lower()
    if hostname == "discord.com" or hostname.endswith(".discord.com"):
        return "discord"
    if hostname.endswith("bandcamp.com"):
        return "bandcamp"
    if any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in ("dropbox.com", "mediafire.com", "mega.nz")
    ):
        return "download"
    return "reference"


def _card_links_get(card: dict[str, typing.Any]) -> list[dict[str, typing.Any]]:
    links: dict[str, dict[str, typing.Any]] = {}
    description = str(card.get("desc") or "")
    for position, match in enumerate(_URL_PATTERN.finditer(description)):
        url = match.group().rstrip(".,;")
        links.setdefault(
            url,
            {
                "link_type": _link_type_get(url),
                "url": url,
                "label": None,
                "sort_order": position,
                "trello_attachment_id": None,
            },
        )

    for attachment in card.get("attachments") or []:
        if not isinstance(attachment, dict) or not attachment.get("url"):
            continue
        url = str(attachment["url"])
        links[url] = {
            "link_type": "attachment",
            "url": url,
            "label": attachment.get("name"),
            "sort_order": attachment.get("pos") or len(links),
            "trello_attachment_id": attachment.get("id"),
        }
    return list(links.values())


def _suggestion_upsert(
    con: sqlite3.Connection,
    card: dict[str, typing.Any],
    list_info: _ListInfo,
    kind: str,
) -> str:
    trello_card_id = str(card["id"])
    row = con.execute(
        "select suggestion_id from suggestions where trello_card_id = ?",
        (trello_card_id,),
    ).fetchone()
    suggestion_id = row["suggestion_id"] if row is not None else id_new()
    description = str(card.get("desc") or "")
    updated_at = str(card.get("dateLastActivity") or "")
    created_at = _created_at_get(trello_card_id, updated_at)
    con.execute(
        """
        insert into suggestions (
            suggestion_id,
            title,
            kind,
            status,
            description,
            requester_name,
            requested_at,
            claimed_by_name,
            sort_order,
            created_at,
            updated_at,
            trello_card_id,
            trello_url
        ) values (
            :suggestion_id,
            :title,
            :kind,
            :status,
            :description,
            :requester_name,
            :requested_at,
            :claimed_by_name,
            :sort_order,
            :created_at,
            :updated_at,
            :trello_card_id,
            :trello_url
        )
        on conflict (trello_card_id) do update set
            title = excluded.title,
            kind = excluded.kind,
            status = excluded.status,
            description = excluded.description,
            requester_name = coalesce(
                suggestions.requester_name, excluded.requester_name
            ),
            requested_at = coalesce(suggestions.requested_at, excluded.requested_at),
            claimed_by_name = excluded.claimed_by_name,
            sort_order = excluded.sort_order,
            updated_at = excluded.updated_at,
            trello_url = excluded.trello_url
        """,
        {
            "suggestion_id": suggestion_id,
            "title": str(card.get("name") or "Untitled suggestion"),
            "kind": kind,
            "status": list_info.status,
            "description": description,
            "requester_name": _requester_name_get(description),
            "requested_at": _requested_at_get(description),
            "claimed_by_name": list_info.claimed_by_name,
            "sort_order": card.get("pos") or 0,
            "created_at": created_at,
            "updated_at": updated_at or created_at,
            "trello_card_id": trello_card_id,
            "trello_url": card.get("url"),
        },
    )
    return suggestion_id


def _trello_import(
    con: sqlite3.Connection,
    board_id: str,
    client: httpx.Client,
) -> TrelloImportResult:
    board_url = f"{_TRELLO_API}/boards/{urllib.parse.quote(board_id, safe='')}"
    lists = _json_list(client, f"{board_url}/lists", {"filter": "all"})
    cards = _json_list(
        client,
        f"{board_url}/cards",
        {
            "filter": "all",
            "attachments": "true",
            "attachment_fields": "id,name,url,pos",
        },
    )
    comments = _comments_get(client, board_url)
    list_names = {str(item["id"]): str(item["name"]) for item in lists}

    suggestion_ids: dict[str, str] = {}
    channel_count = 0
    link_count = 0
    tag_count = 0
    skipped = 0
    try:
        for card in cards:
            list_name = list_names.get(str(card.get("idList") or ""), "")
            list_info = _list_info(list_name)
            if list_info.skip:
                skipped += 1
                continue

            labels = [
                str(label.get("name") or "")
                for label in card.get("labels") or []
                if isinstance(label, dict) and label.get("name")
            ]
            kind = (
                "cleanup" if "Playlist Error / Clean-up" in labels else list_info.kind
            )
            suggestion_id = _suggestion_upsert(con, card, list_info, kind)
            suggestion_ids[str(card["id"])] = suggestion_id

            channel_ids = {
                _CHANNEL_LABELS[label.casefold()]
                for label in labels
                if label.casefold() in _CHANNEL_LABELS
            }
            if list_info.primary_channel_id is not None:
                channel_ids.add(list_info.primary_channel_id)
            primary_channel_id = list_info.primary_channel_id
            if primary_channel_id is None and len(channel_ids) == 1:
                primary_channel_id = next(iter(channel_ids))
            for channel_id in channel_ids:
                con.execute(
                    """
                    insert into suggestion_channels (
                        suggestion_id, channel_id, is_primary
                    ) values (?, ?, ?)
                    on conflict (suggestion_id, channel_id) do update set
                        is_primary = excluded.is_primary
                    """,
                    (
                        suggestion_id,
                        channel_id,
                        int(channel_id == primary_channel_id),
                    ),
                )
                channel_count += 1

            tags = {
                label
                for label in labels
                if label.casefold() not in _CHANNEL_LABELS
                and label != "Playlist Error / Clean-up"
                and label != "Rainwave Meta Content"
            }
            if not list_info.known and list_name:
                tags.add(f"Trello list: {list_name}")
            for tag in tags:
                con.execute(
                    """
                    insert into suggestion_tags (suggestion_id, tag)
                    values (?, ?)
                    on conflict (suggestion_id, tag) do nothing
                    """,
                    (suggestion_id, tag),
                )
                tag_count += 1

            for link in _card_links_get(card):
                con.execute(
                    """
                    insert into suggestion_links (
                        link_id,
                        suggestion_id,
                        link_type,
                        url,
                        label,
                        sort_order,
                        trello_attachment_id
                    ) values (?, ?, ?, ?, ?, ?, ?)
                    on conflict (suggestion_id, url) do update set
                        link_type = excluded.link_type,
                        label = coalesce(excluded.label, suggestion_links.label),
                        sort_order = excluded.sort_order,
                        trello_attachment_id = coalesce(
                            excluded.trello_attachment_id,
                            suggestion_links.trello_attachment_id
                        )
                    """,
                    (
                        id_new(),
                        suggestion_id,
                        link["link_type"],
                        link["url"],
                        link["label"],
                        link["sort_order"],
                        link["trello_attachment_id"],
                    ),
                )
                link_count += 1

        activity_count = 0
        for comment in comments:
            data = comment.get("data") or {}
            card = data.get("card") or {}
            suggestion_id = suggestion_ids.get(str(card.get("id") or ""))
            if suggestion_id is None:
                continue
            member = comment.get("memberCreator") or {}
            con.execute(
                """
                insert into suggestion_activity (
                    activity_id,
                    suggestion_id,
                    activity_type,
                    actor_name,
                    body,
                    created_at,
                    trello_action_id,
                    trello_member_id
                ) values (?, ?, 'comment', ?, ?, ?, ?, ?)
                on conflict (trello_action_id) do update set
                    actor_name = excluded.actor_name,
                    body = excluded.body,
                    created_at = excluded.created_at,
                    trello_member_id = excluded.trello_member_id
                """,
                (
                    id_new(),
                    suggestion_id,
                    member.get("fullName") or member.get("username"),
                    data.get("text"),
                    comment.get("date"),
                    comment.get("id"),
                    member.get("id"),
                ),
            )
            activity_count += 1
        con.commit()
    except Exception:
        con.rollback()
        raise

    result = TrelloImportResult(
        suggestions=len(suggestion_ids),
        channels=channel_count,
        links=link_count,
        tags=tag_count,
        activities=activity_count,
        skipped=skipped,
    )
    log.info("Imported Trello board %s: %s", board_id, result)
    return result


def trello_import(
    con: sqlite3.Connection,
    board_id: str,
    client: httpx.Client | None = None,
) -> TrelloImportResult:
    """Import a Trello board into the native suggestion tables.

    Existing records are updated using their Trello card or action IDs, so repeating
    an import does not create duplicates. The transaction is committed on success.
    """
    if client is not None:
        return _trello_import(con, board_id, client)
    with httpx.Client(follow_redirects=True, timeout=30) as trello_client:
        return _trello_import(con, board_id, trello_client)
