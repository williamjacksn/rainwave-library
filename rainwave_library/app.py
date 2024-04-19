import flask
import waitress

app = flask.Flask(__name__)

@app.route('/')
def index():
    return 'ok'

def main(port: int):
    waitress.serve(app, port=port, ident=None)
