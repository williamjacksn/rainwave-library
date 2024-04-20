import fort
import os


def get_db() -> fort.PostgresDatabase:
    cnx_str = os.getenv('RW_CNX')
    return fort.PostgresDatabase(cnx_str)


def get_songs(db: fort.PostgresDatabase, query: str = None, page: int = 1) -> list[dict]:
    if query is None:
        where_clause = 's.song_verified is true'
    else:
        where_clause = '''
            s.song_verified is true and
            concat_ws(' ', a.album_name, s.song_title, s.song_artist_tag, s.song_filename) ilike %(query)s
        '''
    sql = f'''
        select s.song_id, a.album_name, s.song_title, s.song_artist_tag, s.song_filename
        from r4_songs s
        join r4_albums a on a.album_id = s.album_id
        where {where_clause}
        order by s.song_id
        limit 100 offset %(offset)s
    '''
    params = {
        'query': f'%{query}%',
        'offset': 100 * page
    }
    return db.q(sql, params)
