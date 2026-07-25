import logging
import secrets
import sqlite3
import typing
import urllib.parse
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Suggestion:
    colspan: typing.ClassVar[int] = 8
    kinds: typing.ClassVar[tuple[str, ...]] = (
        "new-album",
        "add-to-existing-album",
        "metadata-update",
        "removal",
    )
    kind_labels: typing.ClassVar[dict[str, str]] = {
        "new-album": "New album",
        "add-to-existing-album": "Add to existing album",
        "metadata-update": "Metadata update",
        "removal": "Removal",
    }
    default_kind: typing.ClassVar[str] = "new-album"
    sort_fields: typing.ClassVar[tuple[tuple[str, str], ...]] = (
        ("status", "Status"),
        ("title", "Suggestion title"),
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
    owner_editable_statuses: typing.ClassVar[tuple[str, ...]] = ("new", "claimed")

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
    kinds: typing.Iterable[str] | None = None,
    include_unassigned_channel: bool = False,
) -> list[Suggestion]:
    query = query.strip() if query else None
    valid_statuses = tuple(
        dict.fromkeys(
            status for status in statuses or () if status in Suggestion.statuses
        )
    )
    status_parameters: list[str | None] = [*valid_statuses]
    status_parameters.extend([None] * (len(Suggestion.statuses) - len(valid_statuses)))
    valid_kinds = tuple(
        dict.fromkeys(kind for kind in kinds or () if kind in Suggestion.kinds)
    )
    kind_parameters: list[str | None] = [*valid_kinds]
    kind_parameters.extend([None] * (len(Suggestion.kinds) - len(valid_kinds)))
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
                :kind_0 is null
                or s.kind in (:kind_0, :kind_1, :kind_2, :kind_3)
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
                (
                    :channel_0 is null
                    and :include_unassigned_channel = 0
                )
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
                or (
                    :include_unassigned_channel = 1
                    and not exists (
                        select 1
                        from suggestion_channels any_channel
                        where any_channel.suggestion_id = s.suggestion_id
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
            "include_unassigned_channel": int(include_unassigned_channel),
            "claimed_by_discord_id": claimed_by_discord_id,
            "offset": 100 * (page - 1),
            "query": f"%{query}%" if query else None,
            "requester_discord_id": requester_discord_id,
            "status_0": status_parameters[0],
            "status_1": status_parameters[1],
            "status_2": status_parameters[2],
            "status_3": status_parameters[3],
            "status_4": status_parameters[4],
            "kind_0": kind_parameters[0],
            "kind_1": kind_parameters[1],
            "kind_2": kind_parameters[2],
            "kind_3": kind_parameters[3],
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


def suggestion_open_count_for_channel(
    con: sqlite3.Connection,
    requester_discord_id: str | None,
    channel_id: int,
) -> int:
    if not requester_discord_id:
        return 0
    row = con.execute(
        """
        select count(*) open_count
        from suggestions s
        where s.requester_discord_id = :requester_discord_id
            and s.status in ('new', 'claimed', 'accepted')
            and exists (
                select 1
                from suggestion_channels sc
                where sc.suggestion_id = s.suggestion_id
                    and sc.channel_id = :channel_id
            )
        """,
        {
            "requester_discord_id": requester_discord_id,
            "channel_id": channel_id,
        },
    ).fetchone()
    return int(row["open_count"])


def suggestion_title_match_statuses(
    con: sqlite3.Connection,
    title: str,
) -> tuple[str, ...]:
    title = title.strip()
    if not title:
        return ()
    row = con.execute(
        """
        select
            max(status in ('new', 'claimed', 'accepted')) open_match,
            max(status = 'declined') declined_match
        from suggestions
        where kind = 'new-album'
            and trim(title) collate nocase = :title
            and status in ('new', 'claimed', 'accepted', 'declined')
        """,
        {"title": title},
    ).fetchone()
    matches = []
    if row["open_match"]:
        matches.append("open-suggestion")
    if row["declined_match"]:
        matches.append("declined-suggestion")
    return tuple(matches)


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


def suggestion_requester_discord_id_get(
    con: sqlite3.Connection,
    requester_name: str,
) -> str | None:
    requester_name = requester_name.strip()
    if not requester_name:
        return None
    row = con.execute(
        """
        select requester_discord_id
        from suggestions
        where trim(requester_name) collate nocase = :requester_name
            and nullif(trim(requester_discord_id), '') is not null
        order by updated_at desc, suggestion_id
        limit 1
        """,
        {"requester_name": requester_name},
    ).fetchone()
    return str(row["requester_discord_id"]) if row is not None else None


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
            order by created_at desc, activity_id desc
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
    kind: str = Suggestion.default_kind,
    links: typing.Iterable[tuple[str, str]] = (),
) -> str:
    title = title.strip()
    if not title:
        msg = "Suggestion title is required."
        raise ValueError(msg)
    if channel_id not in {1, 2, 3, 4, 6}:
        msg = "A valid Rainwave channel is required."
        raise ValueError(msg)
    if kind not in Suggestion.kinds:
        msg = "A valid suggestion type is required."
        raise ValueError(msg)
    description = description.strip()
    if not description:
        msg = "Suggestion details are required."
        raise ValueError(msg)
    normalized_links = tuple((url.strip(), label.strip()) for url, label in links)
    if any(not url or not label for url, label in normalized_links):
        msg = "Every added link requires both a URL and a label."
        raise ValueError(msg)

    suggestion_id = id_new()
    try:
        con.execute(
            """
            insert into suggestions (
                suggestion_id,
                title,
                kind,
                description,
                requester_name,
                requester_discord_id,
                requested_at,
                created_at,
                updated_at
            ) values (
                :suggestion_id,
                :title,
                :kind,
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
                "kind": kind,
                "description": description,
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
        for sort_order, (url, label) in enumerate(normalized_links):
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
                    label,
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
            _activity_insert(
                con,
                suggestion_id,
                activity_type="updated-status",
                actor_name=claimed_by_name,
                actor_discord_id=claimed_by_discord_id,
                old_value="new",
                new_value="claimed",
            )
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
    released_by_name: str,
    claimed_by_discord_id: str,
) -> bool:
    released_by_name = released_by_name.strip()
    claimed_by_discord_id = claimed_by_discord_id.strip()
    if not released_by_name or not claimed_by_discord_id:
        msg = (
            "A Discord display name and user ID are required to release "
            "a suggestion claim."
        )
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
            _activity_insert(
                con,
                suggestion_id,
                activity_type="updated-status",
                actor_name=released_by_name,
                actor_discord_id=claimed_by_discord_id,
                old_value="claimed",
                new_value="new",
            )
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
        msg = "Invalid suggestion type."
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
                requested_at
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
                resolved_at = case
                    when :status in ('uploaded', 'declined')
                        and status != :status
                    then strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    when :status not in ('uploaded', 'declined')
                    then null
                    else resolved_at
                end,
                description = :description,
                requester_name = :requester_name,
                requester_discord_id = :requester_discord_id,
                requested_at = :requested_at,
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


def suggestion_description_update(
    con: sqlite3.Connection,
    suggestion_id: str,
    *,
    requester_discord_id: str,
    description: str,
    actor_name: str | None = None,
) -> bool:
    requester_discord_id = requester_discord_id.strip()
    if not requester_discord_id:
        msg = "A Discord user ID is required to update suggestion details."
        raise ValueError(msg)
    description = description.strip()
    if not description:
        msg = "Suggestion details are required."
        raise ValueError(msg)

    try:
        existing = con.execute(
            """
            select description
            from suggestions
            where suggestion_id = :suggestion_id
                and requester_discord_id = :requester_discord_id
                and status in ('new', 'claimed')
            """,
            {
                "suggestion_id": suggestion_id,
                "requester_discord_id": requester_discord_id,
            },
        ).fetchone()
        if existing is None:
            con.rollback()
            return False
        old_description = str(existing["description"])
        if old_description == description:
            con.rollback()
            return True

        cursor = con.execute(
            """
            update suggestions
            set
                description = :description,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            where suggestion_id = :suggestion_id
                and requester_discord_id = :requester_discord_id
                and status in ('new', 'claimed')
            """,
            {
                "suggestion_id": suggestion_id,
                "requester_discord_id": requester_discord_id,
                "description": description,
            },
        )
        if cursor.rowcount != 1:
            con.rollback()
            return False
        _activity_insert(
            con,
            suggestion_id,
            activity_type="updated-description",
            actor_name=actor_name,
            actor_discord_id=requester_discord_id,
            old_value=old_description,
            new_value=description,
        )
        con.commit()
    except Exception:
        con.rollback()
        raise

    log.info("Updated description for suggestion %s", suggestion_id)
    return True


def suggestion_delete(con: sqlite3.Connection, suggestion_id: str) -> bool:
    try:
        cursor = con.execute(
            "delete from suggestions where suggestion_id = ?",
            (suggestion_id,),
        )
        deleted = cursor.rowcount == 1
        if deleted:
            con.commit()
        else:
            con.rollback()
    except Exception:
        con.rollback()
        raise

    if deleted:
        log.info("Deleted suggestion %s", suggestion_id)
    return deleted


def suggestion_comment_add(
    con: sqlite3.Connection,
    suggestion_id: str,
    *,
    actor_name: str | None,
    actor_discord_id: str | None,
    body: str,
) -> bool:
    body = body.strip()
    if not body:
        msg = "A comment cannot be empty."
        raise ValueError(msg)
    exists = con.execute(
        "select 1 from suggestions where suggestion_id = ?",
        (suggestion_id,),
    ).fetchone()
    if exists is None:
        return False
    try:
        _activity_insert(
            con,
            suggestion_id,
            activity_type="comment",
            actor_name=actor_name,
            actor_discord_id=actor_discord_id,
            body=body,
        )
        con.commit()
    except Exception:
        con.rollback()
        raise

    log.info("Added comment to suggestion %s", suggestion_id)
    return True


def suggestion_link_add(
    con: sqlite3.Connection,
    suggestion_id: str,
    *,
    url: str,
    label: str,
    actor_name: str | None = None,
    actor_discord_id: str | None = None,
    is_staff: bool = False,
) -> bool:
    url = url.strip()
    if not url:
        msg = "A link URL is required."
        raise ValueError(msg)
    owner_discord_id = (actor_discord_id or "").strip()
    exists = con.execute(
        """
        select 1
        from suggestions
        where suggestion_id = :suggestion_id
            and (
                :is_staff = 1
                or (
                    requester_discord_id = :requester_discord_id
                    and status in ('new', 'claimed')
                )
            )
        """,
        {
            "suggestion_id": suggestion_id,
            "requester_discord_id": owner_discord_id,
            "is_staff": int(is_staff),
        },
    ).fetchone()
    if exists is None:
        return False
    duplicate = con.execute(
        "select 1 from suggestion_links where suggestion_id = ? and url = ?",
        (suggestion_id, url),
    ).fetchone()
    if duplicate is not None:
        msg = "This link has already been added."
        raise ValueError(msg)
    next_sort_order = con.execute(
        """
        select coalesce(max(sort_order), -1) + 1 next_sort_order
        from suggestion_links
        where suggestion_id = ?
        """,
        (suggestion_id,),
    ).fetchone()["next_sort_order"]
    try:
        _activity_insert(
            con,
            suggestion_id,
            activity_type="added-link",
            actor_name=actor_name,
            actor_discord_id=actor_discord_id,
            new_value=url,
        )
        con.execute(
            """
            insert into suggestion_links (
                link_id, suggestion_id, link_type, url, label, sort_order
            ) values (?, ?, ?, ?, ?, ?)
            """,
            (
                id_new(),
                suggestion_id,
                _link_type_get(url),
                url,
                label.strip() or None,
                next_sort_order,
            ),
        )
        con.commit()
    except Exception:
        con.rollback()
        raise

    log.info("Added link to suggestion %s", suggestion_id)
    return True


def suggestion_link_delete(
    con: sqlite3.Connection,
    suggestion_id: str,
    link_id: str,
    *,
    actor_name: str | None = None,
    actor_discord_id: str | None = None,
    is_staff: bool = False,
) -> bool:
    owner_discord_id = (actor_discord_id or "").strip()
    try:
        link = con.execute(
            """
            select sl.url
            from suggestion_links sl
            join suggestions s using (suggestion_id)
            where sl.suggestion_id = :suggestion_id
                and sl.link_id = :link_id
                and (
                    :is_staff = 1
                    or (
                        s.requester_discord_id = :requester_discord_id
                        and s.status in ('new', 'claimed')
                    )
                )
            """,
            {
                "suggestion_id": suggestion_id,
                "link_id": link_id,
                "requester_discord_id": owner_discord_id,
                "is_staff": int(is_staff),
            },
        ).fetchone()
        if link is None:
            con.rollback()
            return False

        _activity_insert(
            con,
            suggestion_id,
            activity_type="removed-link",
            actor_name=actor_name,
            actor_discord_id=actor_discord_id,
            old_value=str(link["url"]),
        )
        cursor = con.execute(
            """
            delete from suggestion_links
            where suggestion_id = ? and link_id = ?
            """,
            (suggestion_id, link_id),
        )
        if cursor.rowcount != 1:
            con.rollback()
            return False
        con.commit()
    except Exception:
        con.rollback()
        raise

    log.info("Deleted link %s from suggestion %s", link_id, suggestion_id)
    return True


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
