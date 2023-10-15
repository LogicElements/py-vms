# Coefficient of FE ADC
FADC = 0.0004884


class TimeStats:

    def __init__(self):
        self.idx = 0
        self.rev_count = 0
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

    def append_to_stats(self, idx=0, rev_cnt=0, pm=0, blades=0):
        self.idx = idx
        if self.rev_count != 0 and rev_cnt != self.rev_count + 1:
            self.skipped_rev += 1
        self.rev_count = rev_cnt
        self.pm.append(pm)
        self.blades.append(blades)

    def process(self):
        self.pm_avg = sum(self.pm)/len(self.pm)
        self.pm_max = max(self.pm)
        self.pm_min = min(self.pm)
        self.bl_avg = sum(self.blades)/len(self.blades)
        self.bl_max = max(self.blades)
        self.bl_min = min(self.blades)

    def print(self):
        self.process()
        return {"Idx": self.idx,
                "blades": self.bl_avg, "bl_min": self.bl_min, "bl_max": self.bl_max,
                "pm": self.pm_avg, "pm_min": self.pm_min, "pm_max": self.pm_max,
                "skip": self.skipped_rev}

    def get_logger_stats(self):

        if len(self.logger) < 1024:
            ret = 0, 0, 0
        else:
            avg = sum(self.logger) / len(self.logger) * FADC * 10 - 10
            maxim = max(self.logger) * FADC * 10 - 10
            minim = min(self.logger) * FADC * 10 - 10
            ret = avg, maxim, minim
        self.logger = []
        return ret
