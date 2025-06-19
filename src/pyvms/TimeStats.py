import logging
import collections

import numpy as np

# Coefficient of FE ADC
FADC = 0.0004884


class TimeStats:
    """
    Class for gathering simple statistics of timestamp data (data are dropped) and a vector of
    logger data.
    """

    EMPTY_LOG = np.array([[0.0]*1023])

    def __init__(self):
        self.idx = 0
        self.blade_revolution = 0
        self.blades = []
        self.pm = []

        self.skipped_rev = 0
        self.pm_avg = 0
        self.pm_min = 0
        self.pm_max = 0

        self.bl_avg = 0
        self.bl_min = 0
        self.bl_max = 0

        self.logger = []
        self.logger_revolution = 0
        self.logger_skipped = 0
        self.image = self.EMPTY_LOG
        self.buffer = np.array([[0]])
        self.im_dif = []
        self.line_avg = []
        self.line = None

    def append_to_stats(self, idx=0, rev_cnt=0, pm=0, blades=0):
        """
        Append received parameters of timestamp packet
        :param idx: Channel index (address)
        :param rev_cnt: Revolution count
        :param pm: Phase marker
        :param blades: Number of blades
        :return: None
        """
        self.idx = idx
        if self.blade_revolution != 0 and rev_cnt != self.blade_revolution + 1:
            self.skipped_rev += 1
        self.blade_revolution = rev_cnt
        self.pm.append(pm)
        self.blades.append(blades)

    def process(self):
        """
        Compute min, max, average of PM and blade count
        """
        self.pm_avg = sum(self.pm)/len(self.pm)
        self.pm_max = max(self.pm)
        self.pm_min = min(self.pm)
        self.bl_avg = sum(self.blades)/len(self.blades)
        self.bl_max = max(self.blades)
        self.bl_min = min(self.blades)

    def print(self):
        """
        Compute statistics and return them as a string
        :return: String of statistics
        """
        self.process()
        return {"Idx": self.idx,
                "blades": self.bl_avg, "bl_min": self.bl_min, "bl_max": self.bl_max,
                "pm": self.pm_avg, "pm_min": self.pm_min, "pm_max": self.pm_max,
                "skip": self.skipped_rev}

    def get_logger_stats(self, clear=True):
        """
        Get min, max, average of logger data
        :param clear: Clear internal logger storage
        :return: Average, maximum, minimum of logger data
        """
        if len(self.logger) < 1024:
            ret = 0, 0, 0
        else:
            avg = sum(self.logger) / len(self.logger) * FADC * 10 - 10
            maxim = max(self.logger) * FADC * 10 - 10
            minim = min(self.logger) * FADC * 10 - 10
            ret = avg, maxim, minim
        if clear:
            self.logger = []
        return ret

    def new_logger(self, idx, offset, revolution, data):
        """
        Append new logger data into line and image buffer
        :param idx: Index of channel
        :param offset: Offset of received data
        :param revolution: Revolution counter of logger data
        :param data: Logger data
        :return: None
        """
        # legacy extend data
        self.logger.extend(data)

        # First packet
        if offset == 0:
            # Append data
            if self.line is None:
                self.line = data
            else:
                logging.error("Received first data into non empty line buffer")
        # Second packet
        if offset == 512:
            # Check revolution counter correct value
            if self.logger_revolution != 0 and revolution != self.logger_revolution + 1:
                self.logger_skipped += 1

            # Append data
            if self.line is not None:
                self.line.extend(data)
                if len(self.buffer[0]) != 1024:
                    self.buffer = np.array([self.line])
                else:
                    self.buffer = np.append(self.buffer, [self.line], axis=0)
                self.line = None
            else:
                logging.error("Received second data into empty line buffer")

    def multi_logger_check(self, count_exp=None):
        """
        Check consistency of multi logger data
        :param count_exp: Expected revolution count
        :return: Errors via logging
        """
        for i in range(len(self.buffer) - 1):
            if collections.Counter(self.buffer[i]) == collections.Counter(self.buffer[i+1]):
                logging.error(f"Two loggers seems to be the same at index {i} and {i+1}")

        if self.logger_skipped != 0:
            logging.error(f"Skipped {self.logger_skipped} logs")

        if count_exp is not None and count_exp != len(self.buffer):
            logging.error(f"Wrong number of loggers. Expected {count_exp}, got {len(self.buffer)}")

    def image_limit(self, limit=1000):
        """
        Limit the length of image buffer
        :param limit: Number of most recent entries to keep
        :return: None
        """
        if len(self.buffer) > limit:
            self.buffer = self.buffer[-limit:]

        self.line_avg = np.sum(self.buffer, axis=0) / len(self.buffer)

        self.image = self.buffer - self.line_avg
