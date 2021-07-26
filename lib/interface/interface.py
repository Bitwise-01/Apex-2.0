import flask
import flask_login
from flask import Blueprint

from lib.resp import Resp
from lib.interface.backend import InterfaceBackend

interface = Blueprint('interface', __name__)

@interface.route('/enable-mon-mode', methods=['POST'])
@flask_login.login_required
def set_monitor_mode():
    resp = Resp()

    if not 'interface' in flask.request.form:
        resp.msg = 'An interface is required'
        return flask.jsonify(resp.serialize)

    intf = flask.escape(flask.request.form.get('interface')).strip().lower()
    resp = InterfaceBackend.set_monitor_mode(intf)
    return flask.jsonify(resp.serialize)


@interface.route('/disable-mon-mode', methods=['POST'])
@flask_login.login_required
def set_managed_mode():
    resp = InterfaceBackend.set_managed_mode()
    return flask.jsonify(resp.serialize)


@interface.route('/status', methods=['GET'])
@flask_login.login_required
def status():
    resp = InterfaceBackend.status()
    return flask.jsonify(resp.serialize)
