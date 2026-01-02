import datetime
import os
import pathlib
from typing import TypedDict

import flask
import fort
import htpy

cnx_str = os.getenv("RW_CNX", "")
cnx = fort.PostgresDatabase(cnx_str, maxconn=5)  # ty:ignore[possibly-missing-attribute]

art_dir = pathlib.Path("/var/www/rainwave.cc/album_art")

channels: dict[int | str, str] = {
    1: "Game",
    2: "OC ReMix",
    3: "Covers",
    4: "Chiptune",
    5: "All",
    "1": "Game",
    "2": "OC ReMix",
    "3": "Covers",
    "4": "Chiptune",
    "5": "All",
    "a": "Fallback",
}


def length_display(length: int) -> str:
    """Convert number of seconds to mm:ss format"""
    minutes, seconds = divmod(length, 60)
    return f"{minutes}:{seconds:02d}"


class AlbumDict(TypedDict):
    album_id: int
    album_name: str
    song_count: int


class Album:
    colspan: int = 4
    thead: htpy.Element = htpy.thead[
        htpy.tr(".text-center")[
            htpy.th, htpy.th["ID"], htpy.th["Album name"], htpy.th["Songs"]
        ]
    ]

    def __init__(self, album_data: AlbumDict) -> None:
        self.data = album_data

    @property
    def art_files(self) -> list[pathlib.Path]:
        pattern = f"*_{self.id}_*"
        return sorted(pathlib.Path(art_dir).glob(pattern))

    @property
    def art_table(self) -> htpy.Element:
        src_base = "https://rainwave.cc/album_art"
        files = self.art_files
        prefixes = sorted(set(f.name[0] for f in files))
        return htpy.table(
            ".align-middle.d-block.pt-3.table.table-bordered.table-sm.text-center"
        )[
            htpy.thead[htpy.tr[htpy.th, (htpy.th[channels.get(p)] for p in prefixes)]],
            htpy.tbody[
                (
                    htpy.tr[
                        htpy.th[s],
                        (
                            htpy.td[htpy.img(src=f"{src_base}/{p}_{self.id}_{s}.jpg")]
                            for p in prefixes
                        ),
                    ]
                    for s in (120, 240, 320)
                )
            ],
        ]

    @property
    def detail_table(self) -> htpy.Element:
        return htpy.table(".align-middle.d-block.table")[
            htpy.tbody[
                htpy.tr[htpy.th["ID"], htpy.td(".user-select-all")[htpy.code[self.id]]],
                htpy.tr[htpy.th["Album name"], htpy.td(".user-select-all")[self.name]],
            ]
        ]

    @property
    def id(self) -> int:
        return self.data.get("album_id")

    @property
    def library_link(self) -> htpy.Element:
        return htpy.a(
            ".text-decoration-none",
            href=flask.url_for("albums_detail", album_id=self.id),
        )[self.name]

    @property
    def name(self) -> str:
        return self.data.get("album_name")

    @property
    def song_count(self) -> int:
        return self.data.get("song_count")

    @property
    def tr(self) -> htpy.Element:
        return htpy.tr[
            htpy.td(".text-center.text-nowrap")[
                htpy.a(
                    ".text-decoration-none",
                    href=flask.url_for("albums_detail", album_id=self.id),
                    title="Album detail page",
                )[htpy.i(".bi-info-circle.me-1")]
            ],
            htpy.td(".text-end")[htpy.code[self.id]],
            htpy.td[self.name],
            htpy.td(".text-end")[self.song_count],
        ]


class ListenerDict(TypedDict):
    discord_user_id: int
    group_name: str
    is_discord_user: bool
    radio_last_active: datetime.datetime | None
    rank_title: str
    rating_count: int
    user_id: int
    user_name: str


class Listener:
    colspan: int = 8
    thead: htpy.Element = htpy.thead[
        htpy.tr(".text-center")[
            htpy.th,
            htpy.th["ID"],
            htpy.th["User name"],
            htpy.th["Group"],
            htpy.th["Rank"],
            htpy.th["Ratings"],
            htpy.th["Discord"],
            htpy.th["Last active"],
        ]
    ]

    def __init__(self, listener_data: ListenerDict) -> None:
        self.data = listener_data

    @property
    def detail_table(self) -> htpy.Element:
        return htpy.table(".align-middle.d-block.table")[
            htpy.tbody[
                htpy.tr[htpy.th["ID"], htpy.td(".user-select-all")[htpy.code[self.id]]],
                htpy.tr[htpy.th["User name"], htpy.td(".user-select-all")[self.name]],
                htpy.tr[htpy.th["Rank"], htpy.td(".user-select-all")[self.rank]],
                htpy.tr[
                    htpy.th["Discord user ID"],
                    htpy.td(".user-select-all")[self.discord_id],
                ],
                htpy.tr[
                    htpy.th["Last active"],
                    htpy.td[
                        bool(self.last_active) and self.last_active.date().isoformat()
                    ],
                ],
            ]
        ]

    @property
    def discord_id(self) -> int:
        return self.data.get("discord_user_id")

    @property
    def edit_btn(self) -> htpy.Element:
        return htpy.a(
            ".btn.btn-outline-success",
            href=flask.url_for("listeners_edit", listener_id=self.id),
        )[htpy.i(".bi-pencil"), " Edit listener"]

    @property
    def edit_form(self) -> htpy.Element:
        return htpy.form(method="post")[
            htpy.table(".align-middle.d-block.table")[
                htpy.tbody[
                    htpy.tr[htpy.th["ID"], htpy.td[htpy.code[self.id]]],
                    htpy.tr[htpy.th["User name"], htpy.td[self.name]],
                    htpy.tr[
                        htpy.th[htpy.label(for_="discord_user_id")["Discord user ID"]],
                        htpy.td[
                            htpy.input(
                                "#discord_user_id.form-control",
                                name="discord_user_id",
                                type="text",
                                value=self.discord_id or "",
                            )
                        ],
                    ],
                ]
            ],
            htpy.button(".btn.btn-outline-success", type="submit")[
                htpy.i(".bi-file-earmark-play"), " Save"
            ],
        ]

    @property
    def group(self) -> str:
        return self.data.get("group_name")

    @property
    def id(self) -> int:
        return self.data.get("user_id")

    @property
    def is_discord_user(self) -> bool:
        return self.data.get("is_discord_user")

    @property
    def last_active(self) -> datetime.datetime | None:
        return self.data.get("radio_last_active")

    @property
    def name(self) -> str:
        return self.data.get("user_name")

    @property
    def rank(self) -> str:
        return self.data.get("rank_title")

    @property
    def rating_count(self) -> int:
        return self.data.get("rating_count")

    @property
    def tr(self) -> htpy.Element:
        return htpy.tr[
            htpy.td(".text-center.text-nowrap")[
                htpy.a(
                    ".text-decoration-none",
                    href=flask.url_for("listeners_detail", listener_id=self.id),
                    title="Listener detail page",
                )[htpy.i(".bi-info-circle.me-1")],
                htpy.a(
                    ".text-decoration-none",
                    href=f"https://rainwave.cc/all/#!/listener/{self.id}",
                    rel="noopener",
                    target="_blank",
                    title="Listener profile on rainwave.cc",
                )[htpy.i(".bi-person-badge")],
            ],
            htpy.td(".text-end")[htpy.code[self.id]],
            htpy.td(".user-select-all")[self.name],
            htpy.td[self.group],
            htpy.td(".user-select-all")[self.rank],
            htpy.td[self.rating_count],
            htpy.td(".text-center")[
                self.is_discord_user and htpy.i(".bi-check-lg", title=self.discord_id)
            ],
            htpy.td[bool(self.last_active) and self.last_active.date().isoformat()],
        ]


class SongDict(TypedDict):
    album_name: str
    channels: list[int]
    song_added_on: int
    song_artist_tag: str
    song_fave_count: int
    song_filename: str
    song_groups: list[str]
    song_id: int
    song_length: int
    song_link_text: str
    song_origin_sid: int
    song_rating: float
    song_rating_count: int
    song_request_count: int
    song_title: str
    song_url: str


class Song:
    colspan: int = 11
    thead: htpy.Element = htpy.thead[
        htpy.tr[
            htpy.th(".d-table-cell.d-md-none"),
            htpy.th(".d-table-cell.d-md-none.text-center")["Info"],
            [
                htpy.th(".d-none.d-md-table-cell.text-center")[label]
                for label in (
                    "",
                    "ID",
                    "Origin",
                    "Album",
                    "Title",
                    "Artist",
                    "Rating",
                    "Ratings",
                    "Length",
                    "URL",
                    "Filename",
                )
            ],
        ],
    ]

    def __init__(self, song_data: SongDict) -> None:
        self.data = song_data

    def __len__(self) -> int:
        return self.data.get("song_length")

    @property
    def added_on(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(
            self.data.get("song_added_on"), tz=datetime.UTC
        )

    @property
    def album_name(self) -> str:
        return self.data.get("album_name")

    @property
    def artist_tag(self) -> str:
        return self.data.get("song_artist_tag")

    @property
    def channel_ids(self) -> list[int]:
        return self.data.get("channels")

    @property
    def details_hint(self) -> str:
        return f"Details: {self.album_name} / {self.title}"

    @property
    def download_hint(self) -> str:
        return f"Download: {self.album_name} / {self.title}"

    @property
    def download_url(self) -> str:
        return flask.url_for("songs_download", song_id=self.id)

    @property
    def fave_count(self) -> int:
        return self.data.get("song_fave_count")

    @property
    def filename(self) -> str:
        return self.data.get("song_filename")

    @property
    def groups(self) -> list[str]:
        return self.data.get("song_groups")

    @property
    def id(self) -> int:
        return self.data.get("song_id")

    @property
    def link_text(self) -> str:
        return self.data.get("song_link_text")

    @property
    def origin_channel(self) -> str:
        return channels.get(self.data.get("song_origin_sid"), "Unknown")

    @property
    def rating(self) -> float:
        return self.data.get("song_rating")

    @property
    def rating_count(self) -> int:
        return self.data.get("song_rating_count")

    @property
    def request_count(self) -> int:
        return self.data.get("song_request_count")

    @property
    def stream_hint(self) -> str:
        return f"Stream: {self.album_name} / {self.title}"

    @property
    def title(self) -> str:
        return self.data.get("song_title")

    @property
    def tr(self) -> htpy.Fragment:
        return htpy.fragment[
            htpy.tr[
                htpy.td(".p-2.d-table-cell.d-md-none")[
                    htpy.a(
                        ".btn.btn-outline-primary.mb-1",
                        href=flask.url_for("songs_detail", song_id=self.id),
                        title="Song details",
                    )[htpy.i(".bi-info-circle")],
                    htpy.br,
                    htpy.a(
                        ".btn.btn-outline-primary.mb-1",
                        href=self.download_url,
                        title="Download this song",
                    )[htpy.i(".bi-download")],
                    htpy.br,
                    htpy.a(
                        ".btn.btn-outline-primary",
                        href="#",
                        hx_get=flask.url_for("songs_play", song_id=self.id),
                        hx_target="#audio",
                        title="Play this song",
                    )[htpy.i(".bi-play")],
                ],
                htpy.td(".p-2.d-table-cell.d-md-none")[
                    htpy.i(".bi-disc"),
                    " ",
                    self.album_name,
                    htpy.br,
                    htpy.i(".bi-music-note-beamed"),
                    " ",
                    self.title,
                    htpy.br,
                    htpy.i(".bi-person"),
                    "  ",
                    self.artist_tag,
                    htpy.br,
                    htpy.i(".bi-clock-history"),
                    " ",
                    length_display(len(self)),
                    htpy.br,
                    htpy.i(".bi-award"),
                    f" {self.rating:.2f} ({self.rating_count})",
                    htpy.br,
                    self.url
                    and [
                        htpy.i(".bi-link-45deg"),
                        " ",
                        htpy.a(
                            ".text-decoration-none",
                            href=self.url,
                            target="_blank",
                        )[self.link_text],
                        htpy.br,
                    ],
                ],
                htpy.td(".d-none.d-md-table-cell.text-center.text-nowrap")[
                    htpy.a(
                        ".me-1.text-decoration-none",
                        href=flask.url_for("songs_detail", song_id=self.id),
                        title=self.details_hint,
                    )[htpy.i(".bi-info-circle")],
                    htpy.a(
                        ".me-1.text-decoration-none",
                        href=self.download_url,
                        title=self.download_hint,
                    )[htpy.i(".bi-download")],
                    htpy.a(
                        ".text-decoration-none",
                        href="#",
                        hx_get=flask.url_for("songs_play", song_id=self.id),
                        hx_target="#audio",
                        title=self.stream_hint,
                    )[htpy.i(".bi-play")],
                ],
                htpy.td(".d-none.d-md-table-cell.text-end")[htpy.code[self.id]],
                htpy.td(".d-none.d-md-table-cell.text-nowrap")[self.origin_channel],
                htpy.td(".d-none.d-md-table-cell.user-select-all")[self.album_name],
                htpy.td(".d-none.d-md-table-cell.user-select-all")[self.title],
                htpy.td(".d-none.d-md-table-cell")[self.artist_tag],
                htpy.td(
                    class_=[
                        "d-none",
                        "d-md-table-cell",
                        "text-end",
                        "text-nowrap",
                        {"text-secondary": self.rating == 0},
                    ],
                    title=str(self.rating),
                )[
                    htpy.form(
                        ".d-inline",
                        hx_confirm="Remove this song for low ratings?",
                        hx_post=flask.url_for("songs_remove", song_id=self.id),
                        hx_swap="delete",
                        hx_target="closest tr",
                    )[
                        htpy.input(name="reason", type="hidden", value="Low ratings"),
                        htpy.button(
                            ".btn.btn-link.pe-0.text-danger.text-decoration-none",
                            type="submit",
                        )[htpy.i(".bi-exclamation-circle"), f" {self.rating:.2f}"],
                    ]
                    if 0 < self.rating < 3
                    else f"{self.rating:.2f}"
                ],
                htpy.td(
                    class_=[
                        "d-none",
                        "d-md-table-cell",
                        "text-end",
                        {"text-secondary": self.rating_count == 0},
                    ]
                )[self.rating_count],
                htpy.td(".d-none.d-md-table-cell.text-end")[length_display(len(self))],
                htpy.td(".d-none.d-md-table-cell")[
                    self.url
                    and htpy.a(
                        ".text-decoration-none",
                        href=self.url,
                        target="_blank",
                        title=self.link_text,
                    )[self.url]
                ],
                htpy.td(".d-none.d-md-table-cell.user-select-all")[
                    htpy.code[self.filename]
                ],
            ],
        ]

    @property
    def url(self) -> str:
        return self.data.get("song_url")


def calculate_removed_location(filename: os.PathLike) -> pathlib.Path:
    library_root = pathlib.Path("/icecast")
    relative = pathlib.Path(filename).relative_to(library_root)
    return library_root / "removed" / relative


def get_album(db: fort.PostgresDatabase, album_id: int) -> Album:
    sql = """
        select album_id, album_name
        from r4_albums
        where album_id = %(album_id)s
    """
    params = {"album_id": album_id}
    return Album(db.q_one(sql, params))


def get_album_songs(db: fort.PostgresDatabase, album_id: int) -> list[Song]:
    sql = """
        select
            s.song_id, a.album_name, s.song_title, s.song_artist_tag, s.song_rating,
            s.song_rating_count, s.song_length,s.song_url, s.song_link_text,
            s.song_filename, s.song_origin_sid
        from r4_songs s
        join r4_albums a on a.album_id = s.album_id and s.album_id = %(album_id)s
        where song_verified is true
        order by song_id asc
    """
    params = {"album_id": album_id}
    return [Song(r) for r in db.q(sql, params)]


def get_albums(
    db: fort.PostgresDatabase,
    query: str | None = None,
    page: int = 1,
    sort_col: str = "album_id",
    sort_dir: str = "asc",
) -> list[Album]:
    where_clause = "s.song_verified is true"
    if query:
        where_clause = f"""
            {where_clause}
            and position(
                lower(%(query)s) in concat_ws(
                    ' ',
                    lower(a.album_name),
                    lower(a.album_name_searchable)
                )
            ) > 0
        """

    if sort_dir not in ("asc", "desc"):
        sort_dir = "asc"
    if sort_col not in ("album_id", "album_name", "song_count"):
        sort_col = "album_id"
    if sort_col in ("album_name",):
        sort_clause = f'{sort_col} collate "C" {sort_dir}'
    else:
        sort_clause = f"{sort_col} {sort_dir}"
    if sort_col != "album_id":
        sort_clause = f"{sort_clause}, album_id asc"

    limit_clause = ""
    if page > 0:
        limit_clause = "limit 101 offset %(offset)s"

    sql = f"""
        select a.album_id, a.album_name collate "C", count(*) song_count
        from r4_songs s
        join r4_albums a on a.album_id = s.album_id
        where {where_clause}
        group by a.album_id, a.album_name
        order by {sort_clause}
        {limit_clause}
    """  # noqa: S608
    params = {
        "offset": 100 * (page - 1),
        "query": query,
    }
    return [Album(r) for r in db.q(sql, params)]


def get_albums_missing_art(db: fort.PostgresDatabase) -> list[Album]:
    sql = """
        select album_id, album_name
        from r4_songs
            join r4_albums using (album_id)
            where song_verified is true
            order by album_name
    """
    rows = db.q(sql)
    result = []
    for row in rows:
        album_id = row.get("album_id")
        album_fn = f"a_{album_id}_120.jpg"
        if not art_dir.joinpath(album_fn).exists():
            result.append(Album(row))
    return result


def get_category_for_album(db: fort.PostgresDatabase, album_name: str) -> str | None:
    sql = """
        select g.group_name, count(*) song_count
        from r4_albums a
        join r4_songs s on s.album_id = a.album_id
        join r4_song_group sg on sg.song_id = s.song_id
        join r4_groups g on g.group_id = sg.group_id
        where a.album_name = %(album_name)s
        group by g.group_name
        order by song_count desc, g.group_name
        limit 1
    """
    params = {
        "album_name": album_name,
    }
    for row in db.q(sql, params):
        return row.get("group_name")
    return None


def get_elections(
    db: fort.PostgresDatabase, sid: int, day: datetime.date
) -> list[dict]:
    where_clause = "elec_used is true"

    if sid not in (1, 2, 3, 4, 5):
        sid = 1

    where_clause = f"""
        {where_clause}
        and sid = %(sid)s
        and to_timestamp(elec_start_actual)::date = %(day)s
    """

    sql = f"""
        select
            e.elec_id, elec_start_actual,
            json_agg(
                jsonb_build_object(
                    'entry_id', entry_id,
                    'entry_position', entry_position,
                    'id', s.song_id,
                    'entry_votes', entry_votes,
                    'title', song_title,
                    'album', album_name,
                    'artist', song_artist_tag,
                    'rating', song_rating
                ) order by entry_position
            ) songs
        from r4_elections e
        join r4_election_entries n on n.elec_id = e.elec_id
        join r4_songs s on s.song_id = n.song_id
        join r4_albums a on a.album_id = s.album_id
        where {where_clause}
        group by e.elec_id, elec_start_actual
        order by elec_start_actual, e.elec_id
    """  # noqa: S608
    params = {
        "sid": sid,
        "day": day,
    }

    return db.q(sql, params)


def get_listener(db: fort.PostgresDatabase, listener_id: int) -> Listener:
    sql = """
        select
            u.user_id,
            coalesce(u.radio_username, u.username) as user_name,
            u.discord_user_id,
            case
                when radio_last_active > 0 then to_timestamp(radio_last_active)
            end as radio_last_active,
            r.rank_title
        from phpbb_users u
        left join phpbb_ranks r on r.rank_id = u.user_rank
        where u.user_id = %(user_id)s
    """
    params = {"user_id": listener_id}
    return Listener(db.q_one(sql, params))


def get_listeners(
    db: fort.PostgresDatabase,
    query: str | None = None,
    page: int = 1,
    ranks: list[int] | None = None,
) -> list[Listener]:
    where_clause = "u.user_type <> 2 and u.user_id > 1"
    if query:
        where_clause = f"""
            {where_clause}
            and position(
                lower(%(query)s) in
                lower(concat_ws(' ', u.radio_username, u.username, u.discord_user_id))
            ) > 0
        """
    if ranks:
        where_clause = f"""
            {where_clause}
            and u.user_rank = any(%(ranks)s)
        """
    sql = f"""
        with c as (
            select user_id, count(*) rating_count
            from r4_song_ratings
            where song_rating_user is not null
            group by user_id
        )
        select
            u.discord_user_id,
            case u.group_id
                when 1 then 'Anonymous'
                when 2 then 'Legacy Listeners'
                when 3 then 'Discord Listeners'
                when 5 then 'Admins'
                when 6 then 'Bot'
                when 8 then 'Donors'
                when 18 then 'Managers'
                else concat('Unknown (', group_id::text, ')')
            end as group_name,
            case
                when u.discord_user_id is null then false
                else true
            end as is_discord_user,
            case
                when u.radio_last_active > 0 then to_timestamp(u.radio_last_active)
            end as radio_last_active,
            r.rank_title,
            coalesce(c.rating_count, 0) as rating_count,
            u.user_avatar,
            u.user_id,
            coalesce(u.radio_username, u.username) as user_name,
            u.user_rank
        from phpbb_users u
        left join phpbb_ranks r on r.rank_id = u.user_rank
        left join c on c.user_id = u.user_id
        where {where_clause}
        order by u.user_id
        limit 101 offset %(offset)s
    """  # noqa: S608
    params = {
        "offset": 100 * (page - 1),
        "query": query,
        "ranks": ranks,
    }
    return [Listener(r) for r in db.q(sql, params)]


def get_max_ocr_num(db: fort.PostgresDatabase) -> int:
    sql = """
        select right(s.song_url, 5)::integer ocr_id
        from r4_songs s
        where s.song_verified is true and position('/remix/OCR' in s.song_url) > 0
        order by s.song_url desc
        limit 1
    """
    return db.q_val(sql)


def get_ranks(db: fort.PostgresDatabase) -> list[dict]:
    sql = """
        select distinct r.rank_id, r.rank_title
        from phpbb_users u
        join phpbb_ranks r on r.rank_id = u.user_rank
        order by r.rank_title
    """
    return db.q(sql)


def get_song(db: fort.PostgresDatabase, song_id: int) -> Song:
    sql = """
        with g as (
            select s.song_id, array_agg(g.group_name order by g.group_name) song_groups
            from r4_song_group s
            join r4_groups g on g.group_id = s.group_id
            group by s.song_id
        )
        select
            s.song_added_on, a.album_name, s.song_artist_tag, s.song_fave_count,
            s.song_filename, coalesce(g.song_groups, array[]::text[]) as song_groups,
            s.song_id, s.song_length, s.song_link_text, s.song_rating,
            s.song_rating_count, s.song_request_count, s.song_title, s.song_url,
            s.song_origin_sid
        from r4_songs s
        join r4_albums a on a.album_id = s.album_id
        left join g on g.song_id = s.song_id
        where s.song_id = %(song_id)s
    """
    params = {
        "song_id": song_id,
    }
    return Song(db.q_one(sql, params))


def get_song_filenames(db: fort.PostgresDatabase) -> dict:
    sql = """
        select song_filename, song_verified
        from r4_songs
        order by song_filename
    """
    return {r.get("song_filename"): r.get("song_verified") for r in db.q(sql)}


def get_songs(
    db: fort.PostgresDatabase,
    query: str | None = None,
    page: int = 1,
    sort_col: str = "song_id",
    sort_dir: str = "asc",
    channels: list[int] | None = None,
    include_unrated: bool = True,
) -> list[Song]:
    where_clause = "s.song_verified is true"

    if query:
        where_clause = f"""
            {where_clause}
            and position(
                lower(%(query)s) in
                lower(concat_ws(
                    ' ',
                    a.album_name,
                    s.song_title,
                    s.song_artist_tag,
                    s.song_filename,
                    s.song_url
                ))
            ) > 0
        """

    if not include_unrated:
        where_clause = f"""
            {where_clause}
            and s.song_rating > 0
        """

    if channels is None:
        channels = [1, 2, 3, 4, 5]
    where_clause = f"""
        {where_clause}
        and %(channels)s && c.channels
    """

    if sort_dir not in ("asc", "desc"):
        sort_dir = "asc"
    if sort_col not in (
        "album_name",
        "song_filename",
        "song_id",
        "song_length",
        "song_rating",
        "song_title",
        "song_url",
    ):
        sort_col = "song_id"
    if sort_col in ("album_name", "song_filename", "song_title"):
        sort_clause = f'{sort_col} collate "C" {sort_dir}'
    else:
        sort_clause = f"{sort_col} {sort_dir}"
    if sort_col != "song_id":
        sort_clause = f"{sort_clause}, song_id asc"

    limit_clause = ""
    if page > 0:
        limit_clause = "limit 101 offset %(offset)s"

    sql = f"""
        with c as (
            select song_id, array_agg(sid::integer order by sid) channels
            from r4_song_sid
            where song_exists is true
            group by song_id
        ),
        g as (
            select s.song_id, array_agg(g.group_name order by g.group_name) song_groups
            from r4_song_group s
            join r4_groups g on g.group_id = s.group_id
            group by s.song_id
        )
        select
            a.album_name, c.channels, to_timestamp(s.song_added_on) as song_added_on,
            s.song_artist_tag, s.song_filename,
            coalesce(g.song_groups, array[]::text[]) as song_groups, s.song_id,
            s.song_length, s.song_link_text, s.song_rating, s.song_rating_count,
            s.song_title, s.song_url, s.song_origin_sid
        from r4_songs s
        join r4_albums a on a.album_id = s.album_id
        join c on c.song_id = s.song_id
        left join g on g.song_id = s.song_id
        where {where_clause}
        order by {sort_clause}
        {limit_clause}
    """  # noqa: S608
    params = {
        "channels": channels,
        "offset": 100 * (page - 1),
        "query": query,
    }
    return [Song(r) for r in db.q(sql, params)]


def set_discord_user_id(
    db: fort.PostgresDatabase, user_id: int, discord_user_id: str
) -> None:
    params = {
        "discord_user_id": discord_user_id,
        "user_id": user_id,
    }
    if discord_user_id:
        sql = """
            update phpbb_users
            set discord_user_id = null
            where discord_user_id = %(discord_user_id)s
        """
        db.u(sql, params)
    sql = """
        update phpbb_users
        set discord_user_id = %(discord_user_id)s
        where user_id = %(user_id)s
    """
    db.u(sql, params)
