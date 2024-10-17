import struct
import logging
import math
from .Crc32 import *


class Protocol:
    """
    VMS communication protocol class
    """
    # Packet ID constants
    T_TIMESTAMP = 0x01
    T_LOGGER = 0x02
    T_MASTER = 0x04
    T_FRONTEND = 0x08
    T_FW_UPDATE = 0x10
    T_KEEP_ALIVE = 0x20
    T_MCU = 0x40
    # Constant header values
    HEADER = "LEBVMS"
    SN = 0x0f030100

    # Operation constants
    OP_READ = 0
    OP_WRITE = 1

    # Firmware update constants
    FW_MCU = 2
    FW_MASTER = 4
    FW_FE = 8
    PAGE_SIZE = 1024
    FLASH_PAGE = 256

    def __init__(self):
        """
        Initialize protocol, clear everything
        """
        self.id = 0
        self.flag = 0
        self.address = []
        self.fe = 0
        self.data = []
        self.last_page_ack = 0
        self.nb_pages = 1
        self.fw_version = 0
        self.target = self.FW_MCU
        self.fe_mask = 0
        self.page_id = 0
        self.in_progress = 0
        self.crc = 0

    def parse_config(self, resp):
        """
        Parse received response on configuration socket
        :param resp: Received response packet
        :return: True on successful parsing, False on error
        """
        # Check header constant
        if str(resp[0:6], 'utf-8') != self.HEADER:
            return False
        packet = resp[10]
        # length = 16 + struct.unpack('H', resp[12:14])[0]
        # Switch different packet types
        if packet == self.T_KEEP_ALIVE:
            logging.debug(f"Response for keep alive")
            return True
        if packet == self.T_MCU:
            logging.debug(f"Response for MCU config")
            return self._parse_master(resp[16:])
        if packet == self.T_MASTER:
            logging.debug(f"Response for Master config")
            return self._parse_master(resp[16:])
        if packet == self.T_FRONTEND:
            logging.debug(f"Response for Frontend config")
            return self._parse_master(resp[16:])
        if packet == self.T_FW_UPDATE:
            return self._parse_firmware(resp[16:])
        return False

    def parse_timestamp(self, data, stats=None):
        """
        Parse received packet from timestamp socket
        :param data: Packet Data
        :param stats: Statistics object
        :return: True on success, False on error
        """
        if str(data[0:6], 'utf-8') != self.HEADER:
            return False
        packet = data[10]
        if packet == self.T_KEEP_ALIVE:
            logging.debug(f"Received keep alive")
            return True
        if packet == self.T_TIMESTAMP:
            # logging.debug(f"Timestamp packet")
            return self._parse_timestamp(data[16:], stats)
        if packet == self.T_LOGGER:
            return self._parse_logger(data[16:], stats)
        return False

    @staticmethod
    def check_length(data):
        """
        Check length of received packet based on packet length in header
        :param data: Packet data
        :return: True if received enough data
        """
        if len(data) < 16:
            return False
        length = 16 + struct.unpack('H', data[12:14])[0]
        d_len = len(data)
        if length > d_len:
            return False
        return True

    @staticmethod
    def get_length(data):
        """
        Get length of received packet at zero offset
        :param data: Data buffer for reception
        :return: Length of entire packet
        """
        if len(data) < 16:
            return 0
        else:
            return 16 + struct.unpack('H', data[12:14])[0]

    def keep_alive(self):
        """
        Build keep alive packet
        :return: Keep alive packet data
        """
        pack = self._build_header(self.T_KEEP_ALIVE)
        # Add length
        pack += struct.pack('<L', 4)
        # Add dummy data
        pack += struct.pack('<L', 0)
        return pack

    def mcu_config(self, address, value, operation):
        """
        Build MCU read/write packet
        :param address: Register addresses
        :param value: Register data
        :param operation: Read or write operation
        :return: Packet
        """
        return self._build_packet(address, value, operation, 0, self.T_MCU)

    def master_config(self, address, value, operation):
        """
        Build MASTER read/write packet
        :param address: Register addresses
        :param value: Register data
        :param operation: Read or write operation
        :return: Packet
        """
        return self._build_packet(address, value, operation, 0, self.T_MASTER)

    def fe_config(self, address, value, operation, fe):
        """
        Build FE read/write packet
        :param address: Register addresses
        :param value: Register data
        :param operation: Read or write operation
        :param fe: FE card address
        :return: Packet
        """
        return self._build_packet(address, value, operation, fe, self.T_FRONTEND)

    def _build_packet(self, address, value, operation, fe, packet):
        """
        Build generic packet
        :param address: Register addresses
        :param value: Register data
        :param operation: Read or write operation
        :param fe: FE card address
        :param packet: Packet ID
        :return: Packet
        """
        pack = self._build_header(packet)
        payload = self._build_master(address, value, operation, fe)
        pack += struct.pack('<L', len(payload))
        pack += payload
        return pack

    def _build_master(self, addresses, value, operation, fe):
        """
        Build read/write payload of configuration packets
        :param addresses: Register addresses
        :param value: Register data
        :param operation: Read or write operation
        :param fe: FE card address
        :return: Payload
        """
        # Make array from value if not an array
        try:
            iter(value)
        except TypeError:
            value = [value]
        # Make array from value if not an array
        try:
            iter(addresses)
        except TypeError:
            addresses = [addresses]
        if len(addresses) > len(value):
            for i in range(len(addresses) - len(value)):
                value.append(0)
        if len(addresses) < len(value):
            for i in range(len(value) - len(addresses)):
                addresses.append(addresses[-1])
        msg = struct.pack('<HH', len(value), fe)
        for val, addr in zip(value, addresses):
            msg += struct.pack('<HBBL', addr, operation, self.flag, val)
        self.address = addresses
        self.fe = fe
        return msg

    def _build_header(self, packet=T_KEEP_ALIVE):
        """
        Build packet header
        :param packet: Packet ID
        :return: Header
        """
        self.id += 1
        head = bytearray(self.HEADER, 'utf-8')
        head += struct.pack('<L', self.SN)
        head += bytearray([packet, self.id % 256])
        return head

    @staticmethod
    def _parse_master(payload):
        """
        Parse payload of configuration packet
        :param payload: Payload to parse
        :return: List of parsed values
        """
        [nb, fe] = struct.unpack("<HH", payload[0:4])
        ret = [0] * nb
        for i in range(nb):
            ret[i] = struct.unpack('<L', payload[8+8*i:12+8*i])[0]
        if nb == 1:
            return ret[0]
        return ret

    @staticmethod
    def _parse_timestamp(payload, stats=None):
        """
        Parse packet containing timestamp data
        :param payload: Packet
        :param stats: Object of timestamp statistics
        :return: True if received packet has correct length
        """
        idx = payload[0]
        flags = payload[1]
        blades = struct.unpack("<H", payload[14:16])[0]
        revolution = struct.unpack("<L", payload[16:20])[0]
        pm = struct.unpack("<L", payload[20:24])[0]
        if stats is not None:
            stats.append_to_stats(idx=idx, rev_cnt=revolution, pm=pm, blades=blades)
            # ret = {"idx": idx, "flags": flags, "blades": blades, "rev": revolution, "pm": pm}
            # logging.debug(ret)
        if len(payload) == 24 + blades * 4:
            return True
        return None

    @staticmethod
    def _parse_logger(payload, stats=None):
        """
        Parse packet containing logger data
        :param payload: Packet
        :param stats: Object of timestamp statistics
        :return: True if received packet has correct length
        """
        idx = payload[0]
        nb_data = struct.unpack("<H", payload[2:4])[0]
        offset = struct.unpack("<H", payload[6:8])[0]
        revCnt = struct.unpack("<L", payload[8:12])[0]
        data = list(struct.unpack('%sH' % nb_data, payload[16:]))

        if len(payload) >= 16 + nb_data * 2:
            # Pass logger data into statistics
            if stats is not None:
                stats.new_logger(idx, offset, revCnt, data)
            ret = {"idx": idx, "offset": offset, "revolution": revCnt}
            logging.debug(ret)
            return True
        return None

    def load_firmware(self, filename, target=FW_MCU):
        """
        Load firmware data from file
        :param filename: Binary file to load
        :param target: Target ID
        :return: True on successful loading, False on error
        """
        with open(filename, "rb") as f:
            self.data = bytearray(f.read())
        length = len(self.data)
        extension = length % self.FLASH_PAGE
        if extension != 0:
            self.data += bytearray(self.FLASH_PAGE - extension)
        header = struct.unpack('<L', self.data[0:4])[0]
        self.nb_pages = math.ceil(length / self.PAGE_SIZE)
        self.target = target
        if target == self.FW_MCU and header == 0x20050000:
            return True
        elif target == self.FW_MASTER and header == 0xffffffff and length > 512*1024:
            self._reverse_bit_order()
            return True
        elif target == self.FW_FE and header == 0xffffffff and length < 512*1024:
            self._reverse_bit_order()
            return True
        else:
            return False

    def start_flash(self, fe_mask, crc=None):
        """
        Start flashing procedure to send firmware to target device
        :param fe_mask: Binary mask of FE cards
        :param crc: Pre-computed CRC value. Use None to let Protocol compute it itself
        :return: None
        """
        self.last_page_ack = 0
        self.page_id = 0
        self.fe_mask = fe_mask << 16
        self.in_progress = 1
        if crc is None:
            self.crc = calc_from_byte(self.data)
        else:
            self.crc = crc

    def flash_page(self):
        """
        Build flash packet containing next page of binary data
        :return: Packet
        """
        pack = self._build_header(self.T_FW_UPDATE)
        payload = struct.pack('<HHHHLL', self.target, self.PAGE_SIZE, self.page_id + 1, self.nb_pages, self.crc,
                              self.fe_mask)
        data_len = min(self.PAGE_SIZE, len(self.data) - self.page_id * self.PAGE_SIZE)
        payload += self.data[self.page_id * self.PAGE_SIZE:self.page_id * self.PAGE_SIZE + data_len]
        pack += struct.pack('<L', len(payload))
        pack += payload
        self.page_id += 1
        return pack

    def _parse_firmware(self, payload):
        """
        Parse response of firmware update packet
        :param payload: Payload to parse
        :return: True on successful continuing, False on error
        """
        vals = struct.unpack('<HHHHLL', payload[0:16])
        logging.debug(f"Acked FW update page {vals[2]}/{self.nb_pages} with flags {vals[5] & 0xffff}")
        if vals[0] != self.target or vals[1] != self.PAGE_SIZE: # or vals[3] != self.nb_pages:
            self.in_progress = 0
            return False
        if vals[2] != self.last_page_ack + 1:
            self.in_progress = 0
            return False
        if (vals[5] & 1) == 0:
            self.in_progress = 0
            return False

        self.last_page_ack = vals[2]
        if self.last_page_ack == self.nb_pages:
            self.in_progress = 0
            if (vals[5] & (1 << 8)) == 0:
                logging.debug(f"Last page not acked as Done")
                return False
        return True

    def _reverse_bit_order(self):
        """
        Perform bit reverse operation on loaded binary data for FPGAs
        :return:
        """
        for i in range(len(self.data)):
            self.data[i] = int('{:08b}'.format(self.data[i])[::-1], 2)


