import flask
import flask_login
from flask import Blueprint

from lib.resp import Resp
from lib.handshake.backend import HandshakeBackend

handshake = Blueprint('handshake', __name__)

@handshake.route('/start-process', methods=['POST'])
@flask_login.login_required
def start_process():
    resp = Resp()
    form = flask.request.form

    if not ('bssid' in form and 'essid' in form and 'chann' in form):
        resp.msg = 'This endpoint requires the bssid, essid, and the chann of the target'
        return flask.jsonify(resp.serialize)

    bssid = flask.escape(form.get('bssid')).strip()
    essid = flask.escape(form.get('essid')).strip()
    chann = flask.escape(form.get('chann')).strip()

    if not chann.isdigit():
        resp.msg = 'Channel must be a number'
        return flask.jsonify(resp.serialize)

    if int(chann) < 1 or int(chann) > 14:
        resp.msg = 'Channel must be a number between 1-14'
        return flask.jsonify(resp.serialize)

    resp = HandshakeBackend.start_process(bssid, essid, chann)
    return flask.jsonify(resp.serialize)


@handshake.route('/stop-process', methods=['POST'])
@flask_login.login_required
def stop_process():
    resp = HandshakeBackend.stop_process()
    return flask.jsonify(resp.serialize)


@handshake.route('/output-process', methods=['GET'])
@flask_login.login_required
def output_process():
    def stream():
        if not HandshakeBackend.status().value['target']:
            yield 'data: finished\n\n'
            return

        if HandshakeBackend.status().value['target']['isCaptured']:
            yield 'data: finished\n\n'
            return

        while True:
            target = HandshakeBackend.status().value['target']

            if not target:
                break

            if target['isCaptured']:
                break

            yield 'data: performing attack...\n\n'
            HandshakeBackend.perform_attack()

        yield 'data: finished\n\n'

    return flask.Response(stream(), mimetype='text/event-stream')


@handshake.route('/get-details', methods=['GET'])
@flask_login.login_required
def get_details():
    resp = HandshakeBackend.get_details()
    return flask.jsonify(resp.serialize)


@handshake.route('/status', methods=['GET'])
@flask_login.login_required
def status():
    resp = HandshakeBackend.status()
    return flask.jsonify(resp.serialize)
