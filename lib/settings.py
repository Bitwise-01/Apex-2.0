# enter & exit processes
ENTER_EXIT_PROC = {
    "proc": [
        "dhclient",
        "hostapd",
        "dnsmasq",
        "lighttpd",
        "apache2",
        "airodump-ng",
        "aircrack-ng",
        "aireplay-ng",
    ],
    "services": ["network-manager", "NetworkManager"],
}


# paths
WORKING_PATH = "/tmp"

# interfaces
SCAN_INTERFACE = "apexScan"
EVIL_TWIN_INTERFACE = "apexAP"
DEAUTH_INTERFACE = "apexDeauth"
HANDSHAKE_INTERFACE = "apexHandshake"

# outputs
EVIL_TWIN_OUTPUT = "{WORKING_PATH}/.hostapd.log"
SCAN_OUTPUT = f"{WORKING_PATH}/.accesspoints"
ERROR_LOG = f"{WORKING_PATH}/errors.log"
HANDSHAKE_OUTPUT = f"{WORKING_PATH}/.handshake"
