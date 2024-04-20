import flask
import os
import pathlib
import rainwave_library.models
import waitress
import werkzeug.middleware.proxy_fix
import whitenoise

app = flask.Flask(__name__)
app.wsgi_app = werkzeug.middleware.proxy_fix.ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_port=1)
whitenoise_root = pathlib.Path(__file__).resolve().with_name('static')
app.wsgi_app = whitenoise.WhiteNoise(app.wsgi_app, root=whitenoise_root, prefix='static/')

app.secret_key = os.getenv('SECRET_KEY')


@app.before_request
def before_request():
    flask.g.db = rainwave_library.models.rainwave.get_db()


@app.get('/')
def index():
    return flask.render_template('index.html')


@app.post('/song-table')
def song_table():
    q = flask.request.values.get('q')
    flask.g.songs = rainwave_library.models.rainwave.get_songs(flask.g.db, q)
    return flask.render_template('song-table.html')


def main(port: int):
    waitress.serve(app, port=port, ident=None)
