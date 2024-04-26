import fort
import os
import pathlib


def calculate_removed_location(filename: os.PathLike) -> pathlib.Path:
    library_root = pathlib.Path(os.getenv('LIBRARY_ROOT'))
    relative = pathlib.Path(filename).relative_to(library_root)
    return library_root / 'removed' / relative


def get_db() -> fort.PostgresDatabase:
    cnx_str = os.getenv('RW_CNX')
    return fort.PostgresDatabase(cnx_str)


def get_song(db: fort.PostgresDatabase, song_id: int) -> dict:
    sql = '''
        with g as (
            select s.song_id, array_agg(g.group_name order by g.group_name) song_groups
            from r4_song_group s
            join r4_groups g on g.group_id = s.group_id
            group by s.song_id
        )
        select
            s.song_added_on, a.album_name, s.song_artist_tag, s.song_fave_count, s.song_filename,
            coalesce(g.song_groups, array[]::text[]) as song_groups, s.song_id, s.song_length, s.song_link_text,
            s.song_rating, s.song_rating_count, s.song_request_count, s.song_title, s.song_url
        from r4_songs s
        join r4_albums a on a.album_id = s.album_id
        left join g on g.song_id = s.song_id
        where s.song_id = %(song_id)s
    '''
    params = {
        'song_id': song_id,
    }
    return db.q_one(sql, params)


def get_songs(db: fort.PostgresDatabase, query: str = None, page: int = 1,
              sort_col: str = 'song_id', sort_dir: str = 'asc', channels: list[int] = None) -> list[dict]:

    where_clause = 's.song_verified is true'

    if query:
        where_clause = f'''
            {where_clause}
            and position(
                lower(%(query)s) in
                lower(concat_ws(' ', a.album_name, s.song_title, s.song_artist_tag, s.song_filename))
            ) > 0
        '''

    if channels is None:
        channels = [1, 2, 3, 4, 5]
    where_clause = f'{where_clause} and %(channels)s && c.channels'

    if sort_dir not in ('asc', 'desc'):
        sort_dir = 'asc'
    if sort_col not in ('album_name', 'song_id', 'song_title', 'song_rating', 'song_filename'):
        sort_col = 'song_id'
    sort_clause = f'{sort_col} {sort_dir}'
    if sort_col != 'song_id':
        sort_clause = f'{sort_clause}, song_id asc'

    sql = f'''
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
            a.album_name, c.channels, s.song_added_on, s.song_artist_tag, s.song_filename,
            coalesce(g.song_groups, array[]::text[]) as song_groups, s.song_id, s.song_rating, s.song_rating_count,
            s.song_title
        from r4_songs s
        join r4_albums a on a.album_id = s.album_id
        join c on c.song_id = s.song_id
        left join g on g.song_id = s.song_id
        where {where_clause}
        order by {sort_clause}
        limit 101 offset %(offset)s
    '''
    params = {
        'channels': channels,
        'offset': 100 * (page - 1),
        'query': query,
    }
    return db.q(sql, params)
