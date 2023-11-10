import random
import time
from time import sleep

# Import pyvms
from src.pyvms import *

from lecore.TestFrame import *


class TestCommon:
    conf = None
    time = None
    stats = None

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

    def get_logger(self, meas_time=0.1, fe_addr=16, synced=False):
        """
        Get logger data with given measure period.
        :param meas_time: Measure period for logger
        :param fe_addr: FE card address
        :param synced: Synchronization of logger with PM
        :return Avg, max, min statistics of logger
        """
        divider = int(1e8 * meas_time / 1024)
        self.conf.write_fe(fe_addr, Fe.LOG_DIVIDER, divider)
        self.stats = TimeStats()
        self.time.receive_loop(0.1)
        self.conf.write_fe(fe_addr, Fe.CONTROL_1_LOGGER, 3 if synced else 1)
        self.time.receive_loop(max(meas_time * 2, 0.5), self.stats)
        self.conf.send_keep()
