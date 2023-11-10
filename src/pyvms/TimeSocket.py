import socket
import datetime
import logging
from .Protocol import Protocol


class TimeSocket:
    """
    VMS configuration socket class
    """
    def __init__(self):
        self.ss = None
        self.sock = None
        self.remote = ""
        self.activity = datetime.datetime.now()
        self.pro = Protocol()

    def listen(self, port=50000, con_to=4, rx_to=2):
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
        # self.sock.settimeout(rx_to)

    def close(self):
        """
        Close socket
        :return: None
        """
        if self.sock is not None:
            self.sock.close()
        self.sock = None
        if self.ss is not None:
            self.ss.close()
        self.ss = None

    def receive_loop(self, time=60, stats=None):
        """
        Reception loop for timestamp data
        :param time: Reception time in seconds
        :param stats: Timestamp statistics object
        :return: None
        """
        data = bytearray([])
        # Iterate until end time
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=time)
        while self.activity < end_time:
            ret = True
            self.activity = datetime.datetime.now()

            # Receive more data
            data += self.sock.recv(4096)

            # Are there enough data?
            while ret and len(data) > 16:
                # Check packet format and length
                ret = self.pro.check_length(data)
                if ret:
                    # Correct packet, parse content
                    self.pro.parse_timestamp(data, stats)
                    length = self.pro.get_length(data)
                    data = data[length:]

