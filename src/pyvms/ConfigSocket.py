import socket
import datetime
import logging
import struct
from time import sleep
from .Protocol import Protocol
from .Regs import *

# Coefficient of FE ADC
FADC = 0.0004884
TEMPER_LSB = 0.0625


def concat_thresh_hyst(thresh, hyst):
    """
    Concatenate threshold and hysteresis values into single register
    :param thresh: Threshold in volts (float)
    :param hyst: Hysteresis in volts (float)
    :return: 32-bit value
    """
    thresh = int(((thresh / 10.0) + 1) / FADC)
    thresh = min(max(thresh, 0), 4095)
    hyst = int((hyst / 10.0) / FADC)
    hyst = min(max(hyst, 0), 4095)
    return thresh + (hyst << 16)


def get_thresh_hyst(value):
    """
    Get threshold and hysteresis from 32-bit register value
    :param value: Register value
    :return: Tuple of threshold and hysteresis in floating point Volts
    """
    thresh = (value & 0xffff) * FADC * 10 - 10
    hyst = (value >> 16) * FADC * 10
    return thresh, hyst


def get_fe_temperature(value):
    """
    Get current temperature and temperature alarm of FE card
    :param value: Register value
    :return: Tuple of temperature and temperature alarm
    """
    current = (value & 0x1fff) * TEMPER_LSB
    alarm = (value >> 16) * TEMPER_LSB
    return current, alarm


def get_min_max(value):
    """
    Get min and max values from register value
    :param value: Register value
    :return: Min and Max voltage in floating point Volts
    """
    minimum = (value & 0xffff) * FADC * 10 - 10
    maximum = (value >> 16) * FADC * 10 - 10
    return minimum, maximum


def get_float(value):
    """
    Return float representation of 32-bit register
    :param value: Register value
    :return: Float value
    """
    data = struct.pack('L', value)
    return struct.unpack('f', data)[0]


class ConfigSocket:
    """
    VMS configuration socket class
    """
    def __init__(self):
        self.ss = None
        self.sock = None
        self.remote = ""
        self.activity = datetime.datetime.now()
        self.pro = Protocol()

    def listen(self, port=50001, con_to=4, rx_to=2):
        """
        Listen to incoming TCP connection from VMS
        :param port: TCP port
        :param con_to: Connection timeout in seconds
        :param rx_to: Reception timeout in seconds
        :return: None, but it blocks until connection is open
        """
        self.ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ss.settimeout(con_to)
        self.ss.bind(('', port))
        # Listen to just one connection
        self.ss.listen(1)
        # accept connections from outside
        (self.sock, self.remote) = self.ss.accept()
        logging.info(f"Connected with {self.remote}")
        self.sock.settimeout(rx_to)

    def close(self):
        """
        Close socket
        :return: None
        """
        if self.sock is not None:
            self.sock.close()
        self.sock = None
        self.ss.close()

    def sleep(self, time=1):
        """
        Sleep for given time
        :param time:
        :return:
        """
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=time)
        while datetime.datetime.now() < end_time:
            self.send_keep()
            to_sleep = datetime.datetime.now() - end_time
            sleep(min(1, to_sleep.seconds))
        self.send_keep()

    def send_keep(self):
        """
        Send keep-alive packet and wait for response
        :return: True on success, False on error
        """
        logging.debug(f"Sending keep alive")
        msg = self.pro.keep_alive()
        return self._request_response(msg)

    def read_mcu(self, address):
        """
        Read MCU registers by address
        :param address: Address to read from (may be single value or list of many)
        :return: True on success
        """
        logging.debug(f"Sending Read MCU")
        msg = self.pro.mcu_config(address, [], Protocol.OP_READ)
        return self._request_response(msg)

    def write_mcu(self, address, value):
        """
        Write MCU registers
        :param address: Address to write to (may be single value or list of many)
        :param value: Value to write (length must match the length of address)
        :return: True on success, False on error
        """
        logging.debug(f"Sending Write MCU")
        msg = self.pro.mcu_config(address, value, Protocol.OP_WRITE)
        return self._request_response(msg)

    def read_master(self, address):
        """
        Read MASTER FPGA registers
        :param address: Address to read from (may be single value or list of many)
        :return: True on success, False on error
        """
        logging.debug(f"Sending Read Master")
        msg = self.pro.master_config(address, [], Protocol.OP_READ)
        return self._request_response(msg)

    def write_master(self, address, value):
        """
        Write MASTER FPGA registers
        :param address: Address to write to (may be single value or list of many)
        :param value: Value to write (length must match the length of address)
        :return: True on success, False on error
        """
        logging.debug(f"Sending Write Master")
        msg = self.pro.master_config(address, value, Protocol.OP_WRITE)
        return self._request_response(msg)

    def read_fe(self, fe, address):
        """
        Read FE FPGA registers
        :param fe: Address to read from (may be single value or list of many)
        :param address: Value to write (length must match the length of address)
        :return: True on success, False on error
        """
        logging.debug(f"Sending Read FE")
        msg = self.pro.fe_config(address, [], Protocol.OP_READ, fe)
        return self._request_response(msg)

    def write_fe(self, fe, address, value):
        """
        Write FE FPGA registers
        :param fe: FE card address indexed 1 - 16
        :param address: Address to write to (may be single value or list of many)
        :param value: Value to write (length must match the length of address)
        :return: True on success, False on error
        """
        logging.debug(f"Sending Write FE")
        msg = self.pro.fe_config(address, value, Protocol.OP_WRITE, fe)
        return self._request_response(msg)

    def update_firmware(self, filename, target, mask, crc=None):
        """
        Update firmware of given target device
        :param filename: Name of binary file
        :param target: Target device ID (MCU = 2, MASTER = 4, FE = 8)
        :param mask: Binary mask of FE cards to update (e.g., 0x7 means addresses 1, 2, 3)
        :param crc: Pre-computed CRC value. Use None to let Protocol compute it itself
        :return: True on success, False on error
        """
        logging.debug(f"Starting FW update")
        ret = self.pro.load_firmware(filename, target)
        self.pro.start_flash(mask, crc)
        while self.pro.in_progress and ret:
            msg = self.pro.flash_page()
            ret = self._request_response(msg)
        if ret:
            logging.info(f"Update done")
        return ret

    def _request_response(self, msg):
        """
        Send message, wait for response and parse it
        :param msg: Message packet to send
        :return: True on success, False on error
        """
        ret = False
        self.activity = datetime.datetime.now()
        self.sock.sendall(msg)
        resp = bytearray([])
        while not ret:
            resp += self.sock.recv(2048)
            ret = self.pro.check_length(resp)
        ret = self.pro.parse_config(resp)
        return ret

    def request_logger(self, channels, pm=True, count=1):
        """
        Request logger via Master FPGA internal logic
        :param channels: Bitmap of channels to log
        :param pm: Flag for PM synchronization
        :param count: Number of consecutive loggers to take
        :return: True on success, False on error
        """
        count = max(count - 1, 0)
        value = (count << 20)
        value += (1 << 16) if pm else 0
        value += channels & 0xFFFF
        return self.write_master(VmsRegsMaster.CHANNEL_LOGGER, value)
