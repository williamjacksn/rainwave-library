import datetime
import flask
import functools
import httpx
import os
import pathlib
import rainwave_library.models
import secrets
import urllib.parse
import waitress
import werkzeug.middleware.proxy_fix
import whitenoise

app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_port=1)
whitenoise_root = pathlib.Path(__file__).resolve().with_name('static')
app.wsgi_app = whitenoise.WhiteNoise(app.wsgi_app, root=whitenoise_root, prefix='static/')

app.secret_key = os.getenv('SECRET_KEY')
app.config['PREFERRED_URL_SCHEME'] = os.getenv('SCHEME', 'https')


def external_url_for(endpoint, *args, **kwargs):
    return flask.url_for(endpoint, _scheme=app.config['PREFERRED_URL_SCHEME'], _external=True, *args, **kwargs)


def secure(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        discord_id = flask.session.get('discord_id')
        if discord_id is None:
            return flask.redirect(flask.url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def before_request():
    flask.g.discord_id = flask.session.get('discord_id')
    flask.g.db = rainwave_library.models.rainwave.get_db()
    flask.g.channels = {
        1: 'Game',
        2: 'OC ReMix',
        3: 'Covers',
        4: 'Chiptune',
        5: 'All',
    }


@app.get('/')
def index():
    if flask.g.discord_id is None:
        return flask.render_template('sign-in.html')
    return flask.render_template('index.html')


@app.get('/authorize')
def authorize():
    for k, v in flask.request.values.lists():
        app.logger.debug(f'{k}: {v}')
    if flask.session.get('state') != flask.request.values.get('state'):
        return 'State mismatch', 401
    token_endpoint = 'https://discord.com/api/v10/oauth2/token'
    data = {
        'client_id': os.getenv('OPENID_CLIENT_ID'),
        'client_secret': os.getenv('OPENID_CLIENT_SECRET'),
        'code': flask.request.values.get('code'),
        'grant_type': 'authorization_code',
        'redirect_uri': external_url_for('authorize'),
    }
    resp = httpx.post(token_endpoint, data=data).json()
    access_token = resp.get('access_token')
    guild_id = os.getenv('DISCORD_GUILD_ID')
    guild_member_url = f'https://discord.com/api/v10/users/@me/guilds/{guild_id}/member'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    resp = httpx.get(guild_member_url, headers=headers).json()
    username = resp.get('user', {}).get('username')
    user_id = resp.get('user', {}).get('id')
    user_roles = resp.get('roles')
    app.logger.debug(f'Sign in attempt from {username} with roles {user_roles}')
    staff_role = os.getenv('DISCORD_ROLE_ID_STAFF')
    app.logger.debug(f'Staff role is {staff_role}')
    if staff_role in user_roles:
        app.logger.debug(f'{username} has the correct role')
        flask.session.update({
            'discord_id': user_id,
        })
    else:
        app.logger.debug(f'{username} does not have the correct role')
    return flask.redirect(flask.url_for('index'))


@app.get('/nothing')
@secure
def nothing():
    return ''


@app.get('/sign-in')
def sign_in():
    state = secrets.token_urlsafe()
    flask.session.update({
        'state': state
    })
    redirect_uri = external_url_for('authorize')
    query = {
        'client_id': os.getenv('OPENID_CLIENT_ID'),
        'prompt': 'none',
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'guilds.members.read',
        'state': state,
    }
    auth_endpoint = 'https://discord.com/oauth2/authorize'
    auth_url = f'{auth_endpoint}?{urllib.parse.urlencode(query)}'
    return flask.redirect(auth_url, 307)


@app.get('/sign-out')
def sign_out():
    flask.session.pop('discord_id')
    return flask.redirect(flask.url_for('index'))


@app.get('/songs/<int:song_id>')
@secure
def songs_detail(song_id: int):
    flask.g.song = rainwave_library.models.rainwave.get_song(flask.g.db, song_id)
    flask.g.song_added_on = datetime.datetime.fromtimestamp(flask.g.song.get('song_added_on'), tz=datetime.UTC)
    return flask.render_template('songs/detail.html')


@app.get('/songs/<int:song_id>/download')
@secure
def download_song(song_id: int):
    song = rainwave_library.models.rainwave.get_song(flask.g.db, song_id)
    return flask.send_file(song.get('song_filename'), as_attachment=True)


@app.get('/songs/<int:song_id>/play')
@secure
def play_song(song_id: int):
    flask.g.song = rainwave_library.models.rainwave.get_song(flask.g.db, song_id)
    return flask.render_template('songs/play.html')


@app.get('/songs/<int:song_id>/stream')
@secure
def stream_song(song_id: int):
    song = rainwave_library.models.rainwave.get_song(flask.g.db, song_id)
    return flask.send_file(song.get('song_filename'))


@app.post('/songs/table-rows')
@secure
def song_table_rows():
    for k, v in flask.request.values.lists():
        app.logger.debug(f'{k}: {v}')
    flask.g.q = flask.request.values.get('q')
    flask.g.page = int(flask.request.values.get('page', 1))
    sort_col = flask.request.values.get('sort-col', 'song_id')
    sort_dir = flask.request.values.get('sort-dir', 'asc')
    input_channels = flask.request.values.getlist('channels')
    valid_channels = [int(c) for c in input_channels if c.isdigit() and 0 < int(c) < 6]
    app.logger.debug(f'{valid_channels=}')
    if not valid_channels:
        valid_channels = None
    flask.g.songs = rainwave_library.models.rainwave.get_songs(flask.g.db, flask.g.q, flask.g.page, sort_col, sort_dir,
                                                               valid_channels)
    return flask.render_template('songs/table-rows.html')


def main(port: int):
    waitress.serve(app, port=port, ident=None)
