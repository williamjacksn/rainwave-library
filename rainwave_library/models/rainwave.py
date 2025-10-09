import datetime
import os
import pathlib

import flask
import fort

cnx_str = os.getenv("RW_CNX")
cnx = fort.PostgresDatabase(cnx_str, maxconn=5)


class Song:
    def __init__(self, song_data: dict) -> None:
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
    def url(self) -> str:
        return self.data.get("song_url")


def calculate_removed_location(filename: os.PathLike) -> pathlib.Path:
    library_root = pathlib.Path(os.getenv("LIBRARY_ROOT"))
    relative = pathlib.Path(filename).relative_to(library_root)
    return library_root / "removed" / relative


def get_albums(
    db: fort.PostgresDatabase,
    query: str | None = None,
    page: int = 1,
    sort_col: str = "album_id",
    sort_dir: str = "asc",
) -> list:
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
    if sort_col not in ("album_id", "album_name"):
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
        select distinct a.album_id, a.album_name collate "C"
        from r4_songs s
        join r4_albums a on a.album_id = s.album_id
        where {where_clause}
        order by {sort_clause}
        {limit_clause}
    """  # noqa: S608
    params = {
        "offset": 100 * (page - 1),
        "query": query,
    }
    return db.q(sql, params)


def get_category_for_album(db: fort.PostgresDatabase, album_name: str) -> str:
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


def get_listener(db: fort.PostgresDatabase, listener_id: int) -> dict:
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
    return db.q_one(sql, params)


def get_listeners(
    db: fort.PostgresDatabase,
    query: str | None = None,
    page: int = 1,
    ranks: list[int] | None = None,
) -> list[dict]:
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
    return db.q(sql, params)


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
            s.song_rating_count, s.song_request_count, s.song_title, s.song_url
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
            s.song_title, s.song_url
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
