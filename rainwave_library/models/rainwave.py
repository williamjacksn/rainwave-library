import fort
import os


def get_db() -> fort.PostgresDatabase:
    cnx_str = os.getenv('RW_CNX')
    return fort.PostgresDatabase(cnx_str)


def get_songs(db: fort.PostgresDatabase, query: str = None, page: int = 1) -> list[dict]:
    if query:
        where_clause = '''
            s.song_verified is true and (
                position(lower(%(query)s) in lower(a.album_name)) > 0 or
                position(lower(%(query)s) in lower(s.song_title)) > 0 or
                position(lower(%(query)s) in lower(s.song_artist_tag)) > 0 or
                position(lower(%(query)s) in lower(s.song_filename)) > 0
            )
        '''
    else:
        where_clause = 's.song_verified is true'
    sql = f'''
        select
            a.album_name, s.song_added_on, s.song_artist_tag, s.song_filename, s.song_id, s.song_rating,
            s.song_rating_count, s.song_title
        from r4_songs s
        join r4_albums a on a.album_id = s.album_id
        where {where_clause}
        order by s.song_id
        limit 101 offset %(offset)s
    '''
    params = {
        'query': query,
        'offset': 100 * (page - 1)
    }
    return db.q(sql, params)
