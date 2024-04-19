import flask
import rainwave_library.models
import waitress

app = flask.Flask(__name__)


@app.before_request
def before_request():
    flask.g.db = rainwave_library.models.rainwave.get_db()


@app.route('/')
def index():
    songs = rainwave_library.models.rainwave.get_songs(flask.g.db)
    return f'ok ({len(songs)} songs)'

def main(port: int):
    waitress.serve(app, port=port, ident=None)
