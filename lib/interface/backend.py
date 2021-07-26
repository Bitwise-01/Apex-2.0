import subprocess
from lib.resp import Resp
from lib import settings, utils
from subprocess import getoutput
from lib.interface.mac_gen import MacGen

class InterfaceBackend:

    wlan = None
    monitor_mode = "monitor"
    managed_mode = "managed"

    interfaces = [
        settings.SCAN_INTERFACE,
        settings.DEAUTH_INTERFACE,
        settings.HANDSHAKE_INTERFACE,
        settings.EVIL_TWIN_INTERFACE,
    ]

    @staticmethod
    def __get_interface(intf):
        cmd = f"airmon-ng | grep {intf} | awk 'NR==1{{print $2}}'"
        return getoutput(cmd)

    @staticmethod
    def __disable_interfaces():
        for intf in InterfaceBackend.interfaces:
            cmd = f"iw dev {intf} del"
            getoutput(cmd)

    @staticmethod
    def __enable_interfaces(intf):
        # disable
        getoutput(f"ifconfig {intf} down")
        InterfaceBackend.__disable_interfaces()

        # enable
        for iface in InterfaceBackend.interfaces:
            mode = (
                InterfaceBackend.monitor_mode
                if iface != settings.EVIL_TWIN_INTERFACE
                else InterfaceBackend.managed_mode
            )

            cmd = f"iw dev {intf} interface add {iface} type {mode}"
            subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).wait()
            InterfaceBackend.change_mac(iface, mode, MacGen.generate())

        # up interface
        getoutput(f"ifconfig {intf} up")

    @staticmethod
    def __monitor_mode_enabled():
        for intf in InterfaceBackend.interfaces:
            if not InterfaceBackend.__get_interface(intf):
                return False
        return True

    @staticmethod
    def set_monitor_mode(intf):
        resp = Resp()

        # check if interface exists
        if not InterfaceBackend.__get_interface(intf):
            resp.msg = "Interface not found"
            return resp

        # check what interface it is
        if intf in [i.lower() for i in InterfaceBackend.interfaces]:
            resp.msg = "Invalid interface"
            return resp

        # check if monitor mode is already set
        if InterfaceBackend.__monitor_mode_enabled():
            resp.msg = "Monitor mode is already enabled"
            resp.status = Resp.SUCCESS_CODE
            return resp

        # stop processes
        utils.kill_all()
        utils.stop_services()

        # attempt to create interfaces
        InterfaceBackend.__enable_interfaces(intf)

        # verify
        if not InterfaceBackend.__monitor_mode_enabled():
            resp.msg = "Failed to enable monitor mode"
            return resp

        InterfaceBackend.wlan = intf

        resp.msg = "Successfully enabled monitor mode"
        resp.value = {"interface": intf}
        resp.status = Resp.SUCCESS_CODE
        return resp

    @staticmethod
    def disable_interfaces():
        if InterfaceBackend.__monitor_mode_enabled():
            InterfaceBackend.__disable_interfaces()

    @staticmethod
    def set_managed_mode():
        resp = Resp()

        if not InterfaceBackend.__monitor_mode_enabled():
            resp.msg = "Monitor mode is not enabled"
            return resp

        InterfaceBackend.__disable_interfaces()

        if InterfaceBackend.__monitor_mode_enabled():
            resp.msg = "Failed to disable monitor mode"
            return resp

        # restart services
        utils.restart_services()

        InterfaceBackend.wlan = None

        resp.msg = "Successfully disabled monitor mode"
        resp.status = Resp.SUCCESS_CODE
        return resp

    @staticmethod
    def change_mac(iface, mode, new_mac):
        cmd = f"ifconfig {iface} down && iwconfig {iface} mode {mode} && macchanger -m {new_mac} {iface} && ifconfig {iface} up"
        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).wait()

    @staticmethod
    def status():
        resp = Resp()
        status = {"monitor-mode": False}

        if InterfaceBackend.__monitor_mode_enabled():
            status["interface"] = InterfaceBackend.wlan
            status["monitor-mode"] = True

        resp.value = status
        resp.status = Resp.SUCCESS_CODE
        return resp
