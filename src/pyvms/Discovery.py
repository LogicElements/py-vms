import socket
import struct
import datetime
import argparse


VERSION = '0.1'


class Device:
    """
    VMS device class
    """

    dummy = 0xFFFFFFFF
    request = 'VmsDisco'
    response = 'VmsHere '
    bc_default = "10.0.0.255"
    ip_default = "255.255.255.255"

    def __init__(self):
        self.ip = self.ip_default
        self.server = self.ip_default
        self.version = ""
        self.timestamp = self.dummy
        self.config = self.dummy

    def disco(self):
        """
        Compose discovery packet
        :return: Packet
        """
        packet = bytes(self.request, 'utf8')
        packet += socket.inet_aton(self.ip)
        packet += socket.inet_aton(self.server)
        packet += struct.pack('LL', self.timestamp, self.config)
        return packet

    def parse(self, message, ip):
        """
        Parse data into device properties
        :param message: Message to parse
        :param ip: IP of sender
        :return: Status of parsing
        """
        # Check response header
        if message[:8] == bytes(self.response, 'utf8'):
            message = message[8:]
            # Store properties
            self.ip = ip
            self.server = socket.inet_ntoa(message[4:8])
            self.timestamp = struct.unpack("L", message[8:12])[0]
            self.config = struct.unpack("L", message[12:16])[0]
            self.version = f"{struct.unpack('L', message[16:20])[0]:X}"
            return True
        return False

    def __repr__(self):
        """
        Return representation string
        """
        v = [x for x in vars(self) if not x.startswith("__")]
        return '{' + ', '.join(f"{x}: {getattr(self, x)}" for x in v) + '}'


class Discovery:
    """
    Discovery protocol class
    """

    def __init__(self, broadcast=None, port=4455):
        """
        Set broadcast address and port
        :param broadcast: Broadcast IP address
        :param port: Port
        """
        self.broadcast = broadcast if broadcast is not None else Device.bc_default
        self.port = port

    def probe(self, timeout=1):
        """
        Discover all VMS devices in local network
        :param timeout: Timeout of response to broadcast request
        :return: List of devices
        """
        dev = Device()
        packet = dev.disco()
        devs = self._send_and_response(packet, timeout)
        return devs

    def write(self, dev, timeout=1):
        """
        Write properties into VMS device
        :param dev: Device to write new properties to
        :param timeout: Timeout of response
        :return: Status
        """
        packet = dev.disco()
        devs = self._send_and_response(packet, timeout)
        # Check received response and its content
        if len(devs) != 1 or f"{devs[0]}" != f"{dev}":
            return False
        return True

    def _send_and_response(self, packet, timeout):
        """
        Send packet and wait for response
        :param packet: Packet to send
        :param timeout: Timeout
        :return: List of devices that responded
        """
        # Send broadcast packet
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.settimeout(timeout)
        udp.sendto(packet, (self.broadcast, self.port))

        # Wait up to timeout to receive all responses
        devs = []
        dev = Device()
        while True:
            try:
                # Receive data
                resp_udp, address = udp.recvfrom(4096)

                # Parse data
                if dev.parse(resp_udp, address[0]):
                    devs.append(dev)
                    dev = Device()
            except socket.timeout:
                break
        # Sort devices by IP address
        devs.sort(key=lambda x: x.ip)
        return devs


def discovery_main():

    # Argument parser
    argP = argparse.ArgumentParser(
        prog=f'Discovery',
        description=f'Version {VERSION}. Broadcast discovery protocol to VMS-1201 to get/set communication parameters.'
                    f'## USAGE:'
                    f'> Discovery.py -b 10.0.0.255'
                    f'to discover all VMS devices in the local broadcast address.'
                    f'> Discovery.py -b 10.0.0.255 -v 10.0.0.10 -s 10.0.0.1 -t 30000 -c 30001'
                    f'to set VMS at 10.0.0.10 new server settings 10.0.0.1, 30000, 30001.')
    argP.add_argument('-b', '--broadcast', required=False, metavar='BROADCAST_IP',
                      help='Broadcast IP address, default 10.0.0.255.')
    argP.add_argument('-v', '--vms', required=False, metavar='VMS_IP',
                      help='IP address of VMS of interest. Not needed for discovery, only for setting valeus.')
    argP.add_argument('-s', '--server', required=False, metavar='SERVER_IP',
                      help='IP address of server running VMS setup, e.g., 10.0.0.1.')
    argP.add_argument('-t', '--timestamp', required=False, metavar='PORT',
                      help=f'Timestamp socket port, e.g., 30000.')
    argP.add_argument('-c', '--configuration', required=False, metavar='PORT',
                      help=f'Configuration socket port, e.g., 30001.')
    args = argP.parse_args()

    # Perform discovery
    print(f"=== START === " + datetime.datetime.now().strftime("%y/%m/%d %H:%M:%S ==="))
    d = Discovery(args.broadcast)
    print(f"Discovering VMS devices on {d.broadcast} port {d.port}")
    devices = d.probe()
    print(F"Discovered: {devices}")

    # Get device we want to modify (if any)
    device = None
    if args.vms is not None:
        device = next(x for x in devices if x.ip == args.vms)
    elif len(devices):
        device = devices[0]
    else:
        print("No VMS device discovered")

    # Modify device property
    write_need = False
    if args.server is not None:
        device.server = str(args.server)
        write_need = True
    if args.timestamp is not None:
        device.timestamp = int(args.timestamp)
        write_need = True
    if args.configuration is not None:
        device.config = int(args.configuration)
        write_need = True

    # Write new properties
    if write_need:
        print(F"Writing new settings: {device}")
        ret = d.write(device)
        msg = "OK" if ret else "ERROR"
        print(f"Status of writing new settings is {msg}")
    else:
        print("Nothing to write")

    # End message
    print(f"=== END === " + datetime.datetime.now().strftime("%y/%m/%d %H:%M:%S ==="))
