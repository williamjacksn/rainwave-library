import fort
import os


def get_db() -> fort.PostgresDatabase:
    cnx_str = os.getenv('RW_CNX')
    return fort.PostgresDatabase(cnx_str)


def get_songs(db: fort.PostgresDatabase) -> list[dict]:
    sql = '''
        select *
        from r4_songs
        where song_verified is true
    '''
    return db.q(sql)
