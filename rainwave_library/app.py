import datetime
import flask
import functools
import httpx
import io
import mutagen.id3
import os
import pathlib
import rainwave_library.filters
import rainwave_library.models
import secrets
import string
import textwrap
import time
import urllib.parse
import waitress
import werkzeug.middleware.proxy_fix
import whitenoise
import xlsxwriter

app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_port=1)
whitenoise_root = pathlib.Path(__file__).resolve().with_name('static')
app.wsgi_app = whitenoise.WhiteNoise(app.wsgi_app, root=whitenoise_root, prefix='static/')

app.secret_key = os.getenv('SECRET_KEY')
app.config['PREFERRED_URL_SCHEME'] = os.getenv('SCHEME', 'https')
app.add_template_filter(rainwave_library.filters.length_display)


def external_url_for(endpoint, *args, **kwargs):
    return flask.url_for(endpoint, _scheme=app.config['PREFERRED_URL_SCHEME'], _external=True, *args, **kwargs)


def secure(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in flask.session or flask.session.get('role') == 'member':
            return flask.redirect(flask.url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def before_request():
    app.logger.debug(f'{flask.request.method} {flask.request.path}')
    for k, v in flask.request.values.lists():
        app.logger.debug(f'{k}: {v}')
    flask.session.permanent = True
    flask.g.discord_id = flask.session.get('discord_id')
    flask.g.discord_username = flask.session.get('discord_username')
    flask.g.db = rainwave_library.models.rainwave.cnx
    flask.g.channels = {
        1: 'Game',
        2: 'OC ReMix',
        3: 'Covers',
        4: 'Chiptune',
        5: 'All',
    }


@app.route('/', methods=['GET'])
def index():
    if 'role' not in flask.session:
        return flask.render_template('sign-in.html')
    if flask.session.get('role') == 'member':
        return flask.render_template('not-authorized.html')
    return flask.redirect(flask.url_for('songs'))


@app.route('/api/elections')
def api_elections():
    sid = int(flask.request.values.get('sid', 1))
    day = datetime.date.fromisoformat(flask.request.values.get('day', '2024-01-01'))
    return flask.jsonify({
        'sid': sid,
        'day': day.isoformat(),
        'sched_history': [
            {
                'id': e.get('elec_id'),
                'start_actual': e.get('elec_start_actual'),
                'songs': e.get('songs'),
            } for e in rainwave_library.models.rainwave.get_elections(flask.g.db, sid, day)
        ]
    })


@app.route('/assume-member', methods=['GET'])
@secure
def assume_member():
    flask.session.update({
        'role': 'member',
    })
    return flask.redirect(flask.url_for('index'))


@app.route('/authorize', methods=['GET'])
def authorize():
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
    flask.session.update({
        'discord_id': user_id,
        'discord_username': username,
    })
    user_roles = resp.get('roles')
    app.logger.debug(f'Sign in attempt from {username} with roles {user_roles}')
    staff_role = os.getenv('DISCORD_ROLE_ID_STAFF')
    app.logger.debug(f'Staff role is {staff_role}')
    if staff_role in user_roles:
        app.logger.debug(f'{username} is staff')
        flask.session.update({
            'role': 'staff',
        })
    else:
        app.logger.debug(f'{username} is member')
        flask.session.update({
            'role': 'member',
        })
    return flask.redirect(flask.url_for('index'))


@app.route('/get-ocremix', methods=['GET'])
@secure
def get_ocremix():
    flask.g.max_ocr_num = rainwave_library.models.rainwave.get_max_ocr_num(flask.g.db)
    return flask.render_template('get-ocremix/start.html')


@app.route('/get-ocremix/download', methods=['POST'])
@secure
def get_ocremix_download():
    r = httpx.get(flask.request.values.get('download-from'))
    mp3_data = io.BytesIO(r.content)
    tags = mutagen.id3.ID3(mp3_data)
    tags.delall('TALB')
    tags.add(mutagen.id3.TALB(encoding=3, text=[flask.request.values.get('album')]))
    tags.delall('TIT2')
    tags.add(mutagen.id3.TIT2(encoding=3, text=[flask.request.values.get('title')]))
    tags.delall('TPE1')
    tags.add(mutagen.id3.TPE1(encoding=3, text=[flask.request.values.get('artist')]))
    tags.delall('WXXX')
    tags.add(mutagen.id3.WXXX(encoding=0, url=flask.request.values.get('url')))
    tags.delall('COMM')
    tags.add(mutagen.id3.COMM(encoding=3, text=[flask.request.values.get('link-text')]))
    tags.delall('TCON')
    tags.add(mutagen.id3.TCON(encoding=3, text=[flask.request.values.get('categories')]))
    for tag in ['APIC', 'TCMP', 'TCOM', 'TCOP', 'TDRC', 'TENC', 'TIT1', 'TIT3', 'TOAL', 'TOPE', 'TPE2', 'TPUB', 'TRCK',
                'TSSE', 'TXXX', 'USLT', 'WOAR']:
        tags.delall(tag)
    tags.save(mp3_data)
    target_file = pathlib.Path(get_ocremix_target_file())
    target_file.parent.mkdir(parents=True, exist_ok=True)
    app.logger.debug(f'Saving file to {target_file}')
    target_file.write_bytes(mp3_data.getvalue())
    return flask.render_template('get-ocremix/download.html')


@app.route('/get-ocremix/fetch', methods=['POST'])
@secure
def get_ocremix_fetch():
    ocr_id = int(flask.request.values.get('ocr-id'))
    url = f'https://williamjacksn.github.io/ocremix-data/remix/OCR{ocr_id:05}.json'
    flask.g.ocr_info = httpx.get(url).json()
    app.logger.debug(flask.g.ocr_info)
    album_name = flask.g.ocr_info.get('primary_game')
    default_category = rainwave_library.models.rainwave.get_category_for_album(flask.g.db, album_name)
    if default_category:
        flask.g.categories = [default_category]
    else:
        flask.g.categories = [album_name]
    if flask.g.ocr_info.get('has_lyrics'):
        flask.g.categories.append('Vocal')
    return flask.render_template('get-ocremix/fetch.html')


@app.route('/get-ocremix/target-file', methods=['POST'])
@secure
def get_ocremix_target_file():
    album = rainwave_library.models.mp3.make_safe(flask.request.values.get('album'))
    if set(album) - (set(string.ascii_letters) | set(string.digits)):
        return 'Unsupported character in album.'
    title = rainwave_library.models.mp3.make_safe(flask.request.values.get('title'))
    if set(title) - (set(string.ascii_letters) | set(string.digits)):
        return 'Unsupported character in title'
    first_letter = album[0].lower()
    if first_letter not in string.ascii_lowercase:
        first_letter = '0'
    library_root = pathlib.Path(os.getenv('LIBRARY_ROOT'))
    return str(library_root / 'ocr-all' / first_letter / album / f'{title}.mp3')


@app.route('/listeners', methods=['GET'])
@secure
def listeners():
    flask.g.ranks = rainwave_library.models.rainwave.get_ranks(flask.g.db)
    return flask.render_template('listeners/index.html')


@app.route('/listeners/rows', methods=['POST'])
@secure
def listeners_rows():
    q = flask.request.values.get('q')
    flask.g.page = int(flask.request.values.get('page', 1))
    ranks = list(map(int, flask.request.values.getlist('ranks')))
    flask.g.listeners = rainwave_library.models.rainwave.get_listeners(flask.g.db, q, flask.g.page, ranks)
    return flask.render_template('listeners/rows.html')


@app.route('/nothing', methods=['GET'])
@secure
def nothing():
    return ''


@app.route('/orphan-files', methods=['GET'])
@secure
def orphan_files():
    known_filenames = rainwave_library.models.rainwave.get_song_filenames(flask.g.db)
    orphan_filenames = []
    library_root = pathlib.Path(os.getenv('LIBRARY_ROOT'))
    for mp3 in rainwave_library.models.mp3.yield_all(library_root):
        if mp3 not in known_filenames:
            orphan_filenames.append(str(mp3))
    return str(orphan_filenames)


@app.route('/sign-in', methods=['GET'])
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


@app.route('/sign-out', methods=['GET'])
def sign_out():
    flask.session.pop('discord_id')
    flask.session.pop('discord_username')
    flask.session.pop('role')
    return flask.redirect(flask.url_for('index'))


@app.route('/songs', methods=['GET'])
@secure
def songs():
    return flask.render_template('songs/index.html')


@app.route('/songs/<int:song_id>', methods=['GET'])
@secure
def songs_detail(song_id: int):
    flask.g.song = rainwave_library.models.rainwave.get_song(flask.g.db, song_id)
    flask.g.song_added_on = datetime.datetime.fromtimestamp(flask.g.song.get('song_added_on'), tz=datetime.UTC)
    return flask.render_template('songs/detail.html')


@app.route('/songs/<int:song_id>/download', methods=['GET'])
@secure
def songs_download(song_id: int):
    song = rainwave_library.models.rainwave.get_song(flask.g.db, song_id)
    return flask.send_file(song.get('song_filename'), as_attachment=True)


@app.route('/songs/<int:song_id>/edit', methods=['GET', 'POST'])
@secure
def songs_edit(song_id: int):
    flask.g.song = rainwave_library.models.rainwave.get_song(flask.g.db, song_id)
    if flask.request.method == 'GET':
        return flask.render_template('songs/edit.html')

    kwargs = {
        'album': flask.request.values.get('album'),
        'artist': flask.request.values.get('artist'),
        'categories': flask.request.values.get('categories'),
        'link_text': flask.request.values.get('link-text'),
        'title': flask.request.values.get('title'),
        'url': flask.request.values.get('url'),
    }
    result = rainwave_library.models.mp3.set_tags(flask.g.song.get('song_filename'), **kwargs)
    if result:
        flask.g.edit_result = result
        flask.g.alert_class = 'alert-danger'
    else:
        flask.g.edit_result = 'Song tags updated'
        flask.g.alert_class = 'alert-success'
    time.sleep(1)  # give the scanner some time to catch the file changes and update the database
    return flask.render_template('songs/edit-result.html')


@app.route('/songs/<int:song_id>/play', methods=['GET'])
@secure
def songs_play(song_id: int):
    flask.g.song = rainwave_library.models.rainwave.get_song(flask.g.db, song_id)
    return flask.render_template('songs/play.html')


@app.route('/songs/<int:song_id>/remove', methods=['GET', 'POST'])
@secure
def songs_remove(song_id: int):
    song = rainwave_library.models.rainwave.get_song(flask.g.db, song_id)
    song_filename = pathlib.Path(song.get('song_filename'))
    new_loc = rainwave_library.models.rainwave.calculate_removed_location(song_filename)

    if flask.request.method == 'GET':
        flask.g.song = song
        flask.g.new_loc = new_loc
        return flask.render_template('songs/remove.html')

    reason = flask.request.values.get('reason')
    if new_loc.exists():
        flask.flash(f'Cannot proceed, there is already a file at {new_loc}')
        return flask.redirect(flask.url_for('songs_detail', song_id=song_id))

    new_loc.parent.mkdir(parents=True, exist_ok=True)
    song_filename.rename(new_loc)
    note_text = textwrap.dedent(f'''\
        Song ID: {song_id}
        Original location: {song_filename}
        Removed: {datetime.datetime.now(tz=datetime.UTC)}
        Removed by: {flask.g.discord_username} ({flask.g.discord_id})
        Removal reason: {reason}
        ''')
    note_loc = new_loc.with_suffix('.txt')
    note_loc.write_text(note_text)
    return flask.redirect(flask.url_for('index'))


@app.route('/songs/<int:song_id>/stream', methods=['GET'])
@secure
def stream_song(song_id: int):
    song = rainwave_library.models.rainwave.get_song(flask.g.db, song_id)
    return flask.send_file(song.get('song_filename'))


@app.route('/songs/rows', methods=['POST'])
@secure
def songs_rows():
    flask.g.q = flask.request.values.get('q')
    flask.g.page = int(flask.request.values.get('page', 1))
    sort_col = flask.request.values.get('sort-col', 'song_id')
    sort_dir = flask.request.values.get('sort-dir', 'asc')
    input_channels = flask.request.values.getlist('channels')
    valid_channels = [int(c) for c in input_channels if c.isdigit() and 0 < int(c) < 6]
    app.logger.debug(f'{valid_channels=}')
    if not valid_channels:
        valid_channels = None
    include_unrated = 'include-unrated' in flask.request.values
    flask.g.songs = rainwave_library.models.rainwave.get_songs(flask.g.db, flask.g.q, flask.g.page, sort_col, sort_dir,
                                                               valid_channels, include_unrated)
    return flask.render_template('songs/rows.html')


@app.route('/songs.xlsx', methods=['POST'])
@secure
def songs_xlsx():
    query = flask.request.values.get('q')
    page = 0
    sort_col = flask.request.values.get('sort-col')
    sort_dir = flask.request.values.get('sort-dir')
    input_channels = flask.request.values.getlist('channels')
    channels = [int(c) for c in input_channels if c.isdigit() and 0 < int(c) < 6] or None
    include_unrated = 'include-unrated' in flask.request.values
    data = rainwave_library.models.rainwave.get_songs(flask.g.db, query, page, sort_col, sort_dir, channels,
                                                      include_unrated)
    headers = [
        'song_id', 'channels', 'album_name', 'song_title', 'song_artist_tag', 'song_added_on', 'song_filename',
        'song_groups', 'song_length', 'song_rating', 'song_rating_count', 'song_url', 'song_link_text',
    ]
    col_widths = [len(h) for h in headers]
    output = io.BytesIO()
    workbook_options = {
        'default_date_format': 'yyyy-mm-dd HH:mm:ss',
        'in_memory': True,
        'remove_timezone': True,
        'strings_to_formulas': False,
    }
    workbook = xlsxwriter.Workbook(output, workbook_options)
    rating_format = workbook.add_format({'num_format': '0.00'})
    worksheet = workbook.add_worksheet()
    for i, row in enumerate(data, start=1):
        for j, col_name in enumerate(headers):
            if col_name == 'channels':
                col_data = ', '.join([flask.g.channels[c] for c in row.get(col_name)])
                col_widths[j] = max(col_widths[j], len(col_data))
                worksheet.write(i, j, col_data)
            elif col_name == 'song_groups':
                col_data = ', '.join(row.get(col_name))
                col_widths[j] = max(col_widths[j], len(col_data))
                worksheet.write(i, j, col_data)
            elif col_name == 'song_id':
                col_data = str(row.get(col_name))
                col_widths[j] = max(10, col_widths[j], len(col_data))
                worksheet.write(i, j, col_data)
            elif col_name == 'song_length':
                col_data = rainwave_library.filters.length_display(row.get(col_name))
                col_widths[j] = max(14, col_widths[j], len(col_data))
                worksheet.write(i, j, col_data)
            elif col_name == 'song_rating':
                col_data = row.get(col_name)
                col_widths[j] = max(13, col_widths[j], len(str(col_data)))
                worksheet.write(i, j, col_data, rating_format)
            else:
                col_data = row.get(col_name)
                col_widths[j] = max(col_widths[j], len(str(col_data)))
                worksheet.write(i, j, col_data)
    for i, width in enumerate(col_widths):
        worksheet.set_column(i, i, width)
    table_options = {
        'name': 'songs',
        'columns': [{'header': h} for h in headers]
    }
    worksheet.add_table(0, 0, len(data), len(headers) - 1, table_options)
    workbook.close()
    response = flask.make_response(output.getvalue())
    response.headers.update({
        'Content-Disposition': 'attachment; filename="rainwave-songs.xlsx"',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    return response


def main(port: int):
    waitress.serve(app, port=port, ident=None)
