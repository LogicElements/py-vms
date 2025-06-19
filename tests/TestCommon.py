import random
import time
import datetime
from time import sleep

import matplotlib.pyplot as plt

# Import pyvms
from src.pyvms import *

from lecore.TestFrame import *


class TestCommon:
    conf = None
    time = None
    stats = None
    plot = None

    conf_port = 30001
    time_port = 30000

    @classmethod
    def class_setup(cls):
        """
        Class setup that is called at the beginning of every test case class
        """
        cls.conf = ConfigSocket()
        cls.time = TimeSocket()

    def common_setup(self):
        """
        Test method setup that is called at the beginning of every test method
        """
        self.conf.listen(self.conf_port)

    def common_teardown(self):
        """
        Test method teardown that is called at the end of every test method
        """
        self.conf.close()

    @classmethod
    def class_teardown(cls):
        """
        Class teardown that is called at the end of every test case class
        """
        cls.time.close()
        cls.conf.close()

    def measure_time(self, empty_time=1, eval_time=10):
        """
        Listen on timestamp port for evaluation time. Measured result is in shared statistics object
        :param empty_time: Drop time to empty receive buffer
        :param eval_time: Evaluation time to gather statistics
        """
        self.conf.close()
        self.time.listen(self.time_port)
        self.time.receive_loop(empty_time)
        self.stats = TimeStats()
        self.time.receive_loop(eval_time, self.stats)
        self.time.close()
        self.conf.listen(self.conf_port)

    def get_logger(self, meas_time=None, fe_addr=16, synced=False, count=1, update=False):
        """
        Get logger data with given measure period.
        :param meas_time: Measure period for logger
        :param fe_addr: FE card address
        :param synced: Synchronization of logger with PM
        :param count: Number of loggers
        :return Avg, max, min statistics of logger
        """
        # Compute and write logger divider
        if meas_time is not None:
            divider = int(1e8 * meas_time / 1024)
            self.conf.write_fe(fe_addr, Fe.LOG_DIVIDER, divider)

        # Request logger
        self.conf.request_logger(1 << (fe_addr - 1), synced, count)

        # Receive data for expected amount of time, keep configuration socket alive
        tot_time = max(0.020 * count + 0.5, 1)
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=tot_time)
        data = None
        while end_time > datetime.datetime.now():
            # Receive loop
            data = self.time.receive_loop(0.1, self.stats, data)
            self.conf.send_keep()
            if update:
                self.stats.image_limit(limit=100)
                self.plot = plt.imshow(self.stats.image)
                plt.pause(0.05)

    def print_logger_map(self):
        """
        Print a image map of all loggers
        :return: None
        """
        plt.figure(figsize=(10, 5), dpi=150)
        self.plot = plt.imshow(self.stats.image)
        plt.colorbar(self.plot)
        # plt.legend('', frameon=False)
        # plt.savefig('pixel_plot.png')
        plt.pause(0.05)
