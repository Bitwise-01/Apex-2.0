from lib.settings import WORKING_PATH

# network settings
BASE_IP = "192.168.0.0"
GATEWAY = BASE_IP[:-1] + "1"
MIN_IP = BASE_IP[:-1] + "2"
MAX_IP = BASE_IP[:-1] + "254"
NET_MSK = "255.255.255.0"

LEASE_TIME = 1
DHCP_RANGE = f"{MIN_IP},{MAX_IP},{LEASE_TIME}h"

# configs
DNS_LEASES_PATH = "/var/lib/misc/dnsmasq.leases"
DNS_CONFIG_PATH = f"{WORKING_PATH}/.dnsmasq.conf"

HOSTAPD_CONFIG_PATH = f"{WORKING_PATH}/.hostapd.conf"
HOSTAPD_OUTPUT = f"{WORKING_PATH}/.hostapd.log"

DNS_CONFIG = """
no-resolv
dhcp-authoritative
interface={0}
address=/#/{1}
dhcp-range={2}
dhcp-option=3,{1}
dhcp-option=6,{1}
server=8.8.8.8
log-queries
log-dhcp
listen-address=127.0.0.1
"""

HOSTAPD_CONFIG = """
ssid={}
channel={}
interface={}
driver=nl80211
"""
