import os
import csv
import time
import datetime
import subprocess

from lib import settings
from lib.resp import Resp

from lib.eviltwin.backend import EviltwinBackend
from lib.interface.backend import InterfaceBackend


class Client:
    def __init__(self, mac):
        self.mac = mac
        self.first_seen = None
        self.last_seen = None
        self.power = None
        self.packets = None

    @property
    def serialize(self):
        return {
            "mac": self.mac,
            "power": self.power,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "packets": self.packets,
        }

    def __gt__(self, client):
        a = int(self.packets)
        b = int(self.power)

        c = int(client.packets)
        d = int(client.power)

        if b != -1 and d == -1:
            return True
        elif b == -1 and d != -1:
            return False
        else:
            return a > c


class Accesspoint:
    def __init__(self, bssid, max_time):

        self.max_time = max_time

        # --------------- #

        self.bssid = bssid
        self.essid = "-UNKNOWN-"
        self.chann = -1
        self.power = -100
        self._clients = {}

        # --------------- #

        self.speed = None
        self.privacy = None
        self.cipher = None
        self.authen = None
        self.beacons = None
        self.iv = None

        self.first_seen = None
        self.last_seen = None

    def add_client(self, data):
        mac = data[0]

        client = Client(mac)
        client.first_seen = data[1].strip()
        client.last_seen = data[2].strip()
        client.power = data[3].strip()
        client.packets = data[4].strip()
        self._clients[mac] = client

    def get_pruned_clients(self):
        """Get rid of clients who have been last seen connected a while back"""

        clients = []
        time_fmt1 = "%Y-%m-%d %H:%M:%S"
        time_fmt2 = "%H:%M:%S"

        for client in sorted(self._clients.values(), reverse=True):

            time1 = datetime.datetime.strptime(self.last_seen, time_fmt1)
            time2 = datetime.datetime.strptime(client.last_seen, time_fmt1)

            diff = abs(time2 - time1)
            a = datetime.datetime.strptime(self.max_time, time_fmt2)
            b = datetime.datetime.strptime(str(diff), time_fmt2)

            if a >= b:
                clients.append(client.serialize)

        return clients

    def get_clients(self):
        return [
            client.serialize
            for client in sorted(self._clients.values(), reverse=True)
        ]

    @property
    def ap_score(self):
        return round((100 + self.power) * (len(self._clients) * 0.01), 2)

    @property
    def serialize(self):
        return {
            "bssid": self.bssid,
            "essid": self.essid,
            "chann": self.chann,
            "power": self.power,
            # 'clients': self.get_clients(),
            "clients": self.get_pruned_clients(),
            "ap_score": self.ap_score,
            "speed": self.speed,
            "privacy": self.privacy,
            "cipher": self.cipher,
            "authen": self.authen,
            "beacons": self.beacons,
            "iv": self.iv,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


class APs:
    def __init__(self, essid=None, csv_file=None, is_single_ap=False):
        self.aps = {}
        self.essid = essid
        self.is_alive = False
        self.max_last_seen = None
        self.is_single_ap = is_single_ap
        self.client_max_time = "00:01:15" if not is_single_ap else "00:00:15"
        self.csv_file = (
            csv_file if csv_file else f"{settings.SCAN_OUTPUT}-01.csv"
        )

    def refresh_output(self):
        self.aps = {}

    def remove_output_files(self):
        n = 1

        while True:
            p = f"{settings.SCAN_OUTPUT}-{n:02}.csv"

            if not os.path.exists(p):
                break

            os.remove(p)
            n += 1

    def get_eviltwin_clients(self, eviltwin):
        """Hallucinates evil twin"""

        eviltwin_monitor = eviltwin.eviltwin_monitor

        if not eviltwin_monitor:
            return

        return eviltwin_monitor.get_clients()

    def get_output(self):
        resp = Resp()

        if not os.path.exists(self.csv_file):
            return resp

        with open(self.csv_file, "r") as csvfile:
            self.organize(csv.reader(csvfile, delimiter=","))

        if not self.is_single_ap:
            self.prune_aps()

        aps = self.sort_aps(self.aps)

        # eviltwin = EviltwinBackend.eviltwin()

        # if eviltwin and eviltwin.is_active:

        #     # create an ap for evil twin
        #     eviltwin_info = eviltwin.serialize
        #     eviltwin_ap = Accesspoint(
        #         eviltwin_info["bssid"], self.client_max_time
        #     )
        #     eviltwin_ap.essid = eviltwin_info["essid"]
        #     eviltwin_ap.chann = eviltwin_info["chann"]
        #     eviltwin_ap.power = -1

        #     # add clients
        #     for client in self.get_eviltwin_clients(eviltwin):
        #         eviltwin_ap.add_client(
        #             [client["bssid"], client["first_time"], "", "", ""]
        #         )

        #     # infuse evil twin ap into aps
        #     aps[eviltwin_ap.bssid] = eviltwin_ap.serialize

        resp.value = aps
        resp.status = Resp.SUCCESS_CODE
        return resp

    def sort_aps(self, aps):
        macs = list(aps.keys())

        for i, mac1 in enumerate(macs):
            for n, mac2 in enumerate(macs):

                if i == n:
                    continue

                a = aps[mac1].ap_score
                b = aps[mac2].ap_score

                if i > n:

                    if a > b:
                        macs[i], macs[n] = macs[n], macs[i]
                    elif a == b and aps[mac1].power > aps[mac2].power:
                        macs[i], macs[n] = macs[n], macs[i]

        return {mac: aps[mac].serialize for mac in macs}

    def prune_aps(self):

        if not self.max_last_seen:
            return

        max_time = "00:02:15"
        time_fmt1 = "%Y-%m-%d %H:%M:%S"
        time_fmt2 = "%H:%M:%S"

        for ap in list(self.aps.values()):

            ap_last_seen = datetime.datetime.strptime(ap.last_seen, time_fmt1)

            diff = abs(self.max_last_seen - ap_last_seen)
            a = datetime.datetime.strptime(max_time, time_fmt2)
            b = datetime.datetime.strptime(str(diff), time_fmt2)

            if a < b:
                self.aps.pop(ap.bssid)

    def organize(self, csv):

        for line in csv:

            # where router info is displayed
            if len(line) == 15:
                self.update_info(line)

            # where clients are displayed
            if len(line) == 7:
                self.set_client(line)

    def set_client(self, data):
        # assign
        bssid = data[5].strip()

        # filter
        if any([len(bssid) != 17, not bssid in self.aps]):
            return

        # update
        self.aps[bssid].add_client(data)

    def update_info(self, data):
        # assign
        bssid = data[0].strip()
        chann = data[3].strip()
        power = data[8].strip()
        essid = data[13].strip()

        speed = data[4].strip()
        privacy = data[5].strip()
        cipher = data[6].strip()
        authen = data[7].strip()
        beacons = data[9].strip()
        iv = data[10].strip()

        first_seen = data[1].strip()
        last_seen = data[2].strip()

        if not chann.isdigit() or int(chann) == -1 or int(power) == -1:
            return

        # check for existence
        if not bssid in self.aps:
            self.aps[bssid] = Accesspoint(bssid, self.client_max_time)

        # change essid of hidden ap
        essid = essid if not "\\x00" in essid else "HIDDEN"
        essid = essid if essid else "UNKNOWN"

        # update
        ap = self.aps[bssid]
        ap.essid = essid
        ap.power = int(power)
        ap.chann = f"{int(chann):02}"

        ap.speed = speed
        ap.privacy = privacy
        ap.cipher = cipher
        ap.authen = authen
        ap.beacons = beacons
        ap.iv = iv
        ap.first_seen = first_seen
        ap.last_seen = last_seen

        # update max last_seen
        time_fmt = "%Y-%m-%d %H:%M:%S"
        last_seen = datetime.datetime.strptime(last_seen, time_fmt)

        if not self.max_last_seen:
            self.max_last_seen = last_seen
        elif self.max_last_seen < last_seen:
            self.max_last_seen = last_seen


class AccesspointsBackend:

    __output_file = f"{settings.SCAN_OUTPUT}-01.csv"
    __accesspoints = APs()
    __airodump_process = None

    @staticmethod
    def is_scanning():
        return (
            InterfaceBackend.status().value["monitor-mode"]
            and AccesspointsBackend.__airodump_is_active()
        )

    @staticmethod
    def __airodump_is_active():
        process = AccesspointsBackend.__airodump_process
        return False if not process else process.poll() == None

    @staticmethod
    def start_scan():
        resp = Resp()
        interface_status = InterfaceBackend.status().value
        eviltwin_status = EviltwinBackend.status().value.get("eviltwin", None)

        if not interface_status["monitor-mode"]:
            resp.msg = "Monitor mode must be enabled"
            return resp

        if eviltwin_status:
            if eviltwin_status.get("isActive", False):
                resp.msg = "Eviltwin is active, cannot start scanning"
                return resp

        if AccesspointsBackend.is_scanning():
            resp.msg = "Scanning as already been started"
            resp.status = Resp.SUCCESS_CODE
            return resp

        AccesspointsBackend.__accesspoints.remove_output_files()
        cmd = f"airodump-ng -a -w {settings.SCAN_OUTPUT} --write-interval 1 --output-format csv --berlin 15 {settings.SCAN_INTERFACE}"

        AccesspointsBackend.__airodump_process = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        time.sleep(1.5)

        if AccesspointsBackend.__airodump_is_active():
            resp.msg = "Scanning started successfully"
            resp.status = Resp.SUCCESS_CODE
        else:
            resp.msg = "Failed to start scanning"

        return resp

    @staticmethod
    def stop_scan():
        resp = Resp()

        if not AccesspointsBackend.is_scanning():
            resp.msg = "Scanning is already stopped"
            resp.status = Resp.SUCCESS_CODE
            return resp

        for _ in range(15):
            if not AccesspointsBackend.__airodump_is_active():
                break

            AccesspointsBackend.__airodump_process.kill()
            time.sleep(1)

        if not AccesspointsBackend.__airodump_is_active():
            AccesspointsBackend.__airodump_process = None
            resp.msg = "Scanning stopped successfully"
            resp.status = Resp.SUCCESS_CODE
        else:
            resp.msg = "Failed to stop scanning"

        return resp

    @staticmethod
    def scan_output():
        resp = Resp()

        if not AccesspointsBackend.__airodump_is_active:
            resp.msg = "Scanning is stopped"
            return resp

        if not os.path.exists(AccesspointsBackend.__output_file):
            resp.msg = f"Cannot locate {AccesspointsBackend.__output_file}"
            return resp

        resp = AccesspointsBackend.__accesspoints.get_output()
        return resp

    @staticmethod
    def get_aps():
        resp = Resp()
        resp.value = AccesspointsBackend.__accesspoints.get_output()
        resp.status = Resp.SUCCESS_CODE
        return resp

    @staticmethod
    def refresh_output():
        resp = Resp()
        AccesspointsBackend.__accesspoints.refresh_output()
        resp.status = Resp.SUCCESS_CODE
        return resp

    @staticmethod
    def status():
        resp = Resp()
        status = {"scanning": AccesspointsBackend.is_scanning()}
        resp.value = status
        resp.status = Resp.SUCCESS_CODE
        return resp
