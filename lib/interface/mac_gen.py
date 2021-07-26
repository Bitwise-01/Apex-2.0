import random


class MacGen:
    pre = [
        '00:aa:02',  # Intel
        '00:13:49',  # Zyxel
        '00:40:0b',  # Cisco
        '00:1c:df',  # Belkin
        '00:24:01',  # D-link
        '00:e0:4c',  # Realtek
        '00:e0:ed',  # Silicom
        '00:0f:b5',  # Netgear
        '00:27:19',  # Tp-link
        '00:0a:f7',  # Broadcom
    ]

    post = 'abcdef0123456789'

    @staticmethod
    def get_prefix():
        return random.choice(MacGen.pre)

    @staticmethod
    def get_postfix():
        s = ''

        for _ in range(3):
            s += f':{random.choice(MacGen.post)}{random.choice(MacGen.post)}'

        return s

    @staticmethod
    def generate():
        return MacGen.get_prefix() + MacGen.get_postfix()

    @staticmethod
    def clone(mac):
        while True:
            new_mac = mac[:9] + random.choice(MacGen.post) + mac[10:]

            if new_mac.lower() != mac.lower():
                return new_mac
