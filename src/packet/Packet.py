from __future__ import annotations
import importlib
import string
import re
import random
from ipaddress import IPv4Address, IPv6Address
import scapy.all as scapy
from scapy.layers import dhcp, dhcp6, dns, http, inet, inet6, l2, ntp

class Packet:

    # List of all alphanumerical characters
    ALPHANUM = list(bytes(string.ascii_letters + string.digits, "utf-8"))

    # Modifiable fields, will be overridden by child classes
    fields = {}


    @classmethod
    def init_packet(c, protocol: str, packet: scapy.Packet, id: int = 0) -> Packet:
        """
        Factory method to create a packet of a given protocol.

        :param protocol: Packet highest layer protocol.
        :param packet: Scapy Packet to be edited.
        :param id: Packet integer identifier.
        :return: Packet of given protocol,
                 or generic Packet if protocol is not supported.
        """
        try:
            # Try creating specific packet if possible
            protocol = protocol.replace(" ", "_")
            if protocol == "IP" and packet.getfieldval("version") == 4:
                protocol = "IPv4"
            elif protocol == "IP" and packet.getfieldval("version") == 6:
                protocol = "IPv6"
            module = importlib.import_module(f"packet.{protocol}")
            cls = getattr(module, protocol)
            return cls(packet, id)
        except ModuleNotFoundError:
            # Impossible to create specific packet, create generic packet
            return Packet(packet, id)


    def __init__(self, packet: scapy.Packet, id: int = 0) -> None:
        """
        Generic packet constructor.

        :param packet: Scapy Packet to be edited.
        """
        self.id = id
        self.packet = packet
        try:
            self.layer = packet.getlayer(self.name)
        except AttributeError:
            self.layer = packet.lastlayer()

    
    def get_packet(self) -> scapy.Packet:
        """
        Get Scapy packet.

        :return: Scapy Packet.
        """
        return self.packet


    def tweak(self) -> None:
        """
        Randomly edit one packet field.
        """
        # Get field which will be modified
        field, value_type = random.choice(list(self.fields.items()))
        # Store old value of field
        old_value = self.layer.getfieldval(field)

        # Modify field value until it is different from old value
        new_value = old_value
        while new_value == old_value:

            if isinstance(value_type, list):
                # Field value is a list
                # Choose randomly a value from the list
                values = value_type
                new_value = old_value
                # Randomly pick new value
                new_value = bytes(random.choice(values), "utf-8")

            elif "int" in value_type:
                # Field value is an integer
                # Generate a random integer between given range
                if value_type == "int":
                    # No range given, default is 0-65535
                    new_value = random.randint(0, 65535)
                else:
                    # Range given
                    pattern = re.compile(r"int\[\s*(?P<start>\d+),\s*(?P<end>\d+)\s*\]")
                    match = pattern.match(value_type)
                    start = int(match.group("start"))
                    end = int(match.group("end"))
                    new_value = random.randint(start, end)

            elif value_type == "str":
                # Field value is a string
                # Randomly change one character
                char = random.choice(Packet.ALPHANUM)
                new_value = list(old_value)
                new_value[random.randint(0, len(new_value) - 1)] = char
                new_value = bytes(new_value)

            elif value_type == "port":
                # Field value is an port number
                # Generate a random port number between 1024 and 65535
                new_value = random.randint(1024, 65535)

            elif value_type == "ipv4":
                # Field value is an IPv4 address
                # Generate a random IPv4 address
                new_value = str(IPv4Address(random.randint(0, IPv4Address._ALL_ONES)))

            elif value_type == "ipv6":
                # Field value is an IPv6 address
                # Generate a random IPv6 address
                new_value = str(IPv6Address(random.randint(0, IPv6Address._ALL_ONES)))
            
        # Set new value for field
        print(f"Packet {self.id}: {self.name}.{field} = {old_value} -> {new_value}")
        self.layer.setfieldval(field, new_value)

        # Update checksums
        del self.packet.getlayer(1).len
        del self.packet.getlayer(1).chksum
        if self.packet.getlayer(2).name == "UDP":
            del self.packet.getlayer(2).len
        del self.packet.getlayer(2).chksum
        self.packet = scapy.Ether(self.packet.build())