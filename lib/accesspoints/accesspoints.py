import time
import json
import flask
import flask_login
from flask import Blueprint
from lib.accesspoints.backend import AccesspointsBackend


accesspoints = Blueprint("accesspoints", __name__)

@accesspoints.route("/start-scan", methods=["POST"])
@flask_login.login_required
def start_scan():
    resp = AccesspointsBackend.start_scan()
    return flask.jsonify(resp.serialize)


@accesspoints.route("/stop-scan", methods=["POST"])
@flask_login.login_required
def stop_scan():
    resp = AccesspointsBackend.stop_scan()
    return flask.jsonify(resp.serialize)


@accesspoints.route("/scan-output", methods=["GET"])
@flask_login.login_required
def scan_output():
    def stream():
        while AccesspointsBackend.status().value["scanning"]:
            resp = AccesspointsBackend.scan_output()
            yield f"data: {json.dumps(resp.serialize)}\n\n"
            time.sleep(0.5)
        yield "data: finished\n\n"

    return flask.Response(stream(), mimetype="text/event-stream")


@accesspoints.route("/get-aps")
@flask_login.login_required
def get_aps():
    resp = AccesspointsBackend.get_aps().value
    resp.value = resp.value
    return flask.jsonify(resp.serialize)


@accesspoints.route("/refresh-output", methods=["POST"])
@flask_login.login_required
def refresh_output():
    resp = AccesspointsBackend.refresh_output()
    return flask.jsonify(resp.serialize)


@accesspoints.route("/status", methods=["GET"])
@flask_login.login_required
def status():
    resp = AccesspointsBackend.status()
    return flask.jsonify(resp.serialize)
