import logging

import unittest

from TestCommon import *

logging.getLogger().setLevel(logging.DEBUG)


class TestCommunication(unittest.TestCase, TestCommon):
    """
    Basic communication test case
    """
    # Local variables and settings
    RECEIVE_SEC = 10

    # Block of unittest methods override

    @classmethod
    def setUpClass(cls):
        cls.class_setup()

    def setUp(self):
        self.common_setup()

        # Get all active cards
        self.fe_cards = self.conf.read_master(Master.CHANNEL_ON)
        self.fe_addr = [i + 1 for i in range(16) if self.fe_cards & (1 << i)]

    def tearDown(self):
        self.common_teardown()

    @classmethod
    def tearDownClass(cls):
        cls.class_teardown()

    # Test methods

    def test001_get_fe_cards(self):
        print(f"FE cards at addresses {self.fe_addr}")

    def test002_set_threshold(self):
        # For each active FE card
        for addr in self.fe_addr:
            # Get analog minimum and maximum from FE card
            value = self.conf.read_fe(addr, Fe.MINIMUM_MAXIMUM)
            minim, maxim = get_min_max(value)
            # Compute new values of threshold and hysteresis
            thresh = (minim + maxim) / 2 + (maxim - minim) * 0.1
            hyster = max((maxim - minim) * 0.1, 0.05)
            value = concat_thresh_hyst(thresh, hyster)
            # Write new values into FE card
            self.conf.write_fe(addr, Fe.THRESHOLD_HYSTERESIS, value)

    def test003_get_threshold(self):
        # For each active FE card
        for addr in self.fe_addr:
            # Get threshold and hysteresis values from a shared register
            value = self.conf.read_fe(addr, Fe.THRESHOLD_HYSTERESIS)
            thres, hyst = get_thresh_hyst(value)
            print(f"FE {addr}, threshold {thres:.5f} V, hysteresis {hyst:.5f} V")

    def test010_receive_timestamp(self):
        print(f"Run timestamp receive loop for {self.RECEIVE_SEC} seconds")
        # Receive data for given time and print statistics
        self.measure_time(eval_time=self.RECEIVE_SEC)
        print(self.stats.print())

    def test020_get_logger(self):
        # Start listening on timestamp socket
        self.time.listen(self.time_port)

        COUNT = 800

        # For each active FE card
        for addr in self.fe_addr:
            self.stats = TimeStats()
            # Receive Timestamp for some time to drop all buffered data
            self.time.receive_loop(1)
            # Get logger and basic statistics
            self.get_logger(fe_addr=addr, synced=True, count=COUNT)
            avg, maxim, minim = self.stats.get_logger_stats(clear=False)
            print(f"FE {addr}, logger average {avg:.3f} V, min {minim:.3f} V, max {maxim:.3f} V")
            # Print raw data
            print(len(self.stats.logger))
            self.stats.multi_logger_check(count_exp=COUNT)
            # Show image
            self.print_logger_map()
            # Clear logger buffer
            self.stats.get_logger_stats()

