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
    id: str
    title: str
    kind: str
    status: str
    archived: bool
    description: str
    requester_name: str | None
    requested_at: str | None
    claimed_by_name: str | None
    channel_ids: tuple[int, ...]
    tags: tuple[str, ...]


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


def suggestions_get(
    con: sqlite3.Connection,
    query: str | None,
    status: str | None,
    page: int,
    include_archived: bool = False,
) -> list[Suggestion]:
    query = query.strip() if query else None
    valid_statuses = {"new", "claimed", "fulfilled", "declined", "processed"}
    if status not in valid_statuses:
        status = None
    page = max(page, 1)
    rows = con.execute(
        """
        select
            s.suggestion_id,
            s.title,
            s.kind,
            s.status,
            s.archived,
            s.description,
            s.requester_name,
            s.requested_at,
            s.claimed_by_name,
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
        where (:include_archived or not s.archived)
            and (:status is null or s.status = :status)
            and (
                :query is null
                or s.title like :query
                or s.description like :query
                or coalesce(s.requester_name, '') like :query
                or coalesce(s.claimed_by_name, '') like :query
            )
        order by
            s.archived,
            case s.status
                when 'new' then 1
                when 'claimed' then 2
                when 'processed' then 3
                when 'fulfilled' then 4
                when 'declined' then 5
            end,
            s.sort_order,
            s.title collate nocase,
            s.suggestion_id
        limit 101 offset :offset
        """,
        {
            "include_archived": int(include_archived),
            "offset": 100 * (page - 1),
            "query": f"%{query}%" if query else None,
            "status": status,
        },
    ).fetchall()
    return [
        Suggestion(
            id=row["suggestion_id"],
            title=row["title"],
            kind=row["kind"],
            status=row["status"],
            archived=bool(row["archived"]),
            description=row["description"],
            requester_name=row["requester_name"],
            requested_at=row["requested_at"],
            claimed_by_name=row["claimed_by_name"],
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
        for row in rows
    ]


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
        return _ListInfo(status="fulfilled")
    if name == "Declined":
        return _ListInfo(status="declined")
    if name == "Processed for Chill":
        return _ListInfo(status="processed", primary_channel_id=6)
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
            archived,
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
            :archived,
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
            archived = excluded.archived,
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
            "archived": int(bool(card.get("closed"))),
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
