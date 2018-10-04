from artiq.experiment import *

class WallTime(EnvExperiment):
    def build(self):
        self.setattr_device("core")

    @kernel
    def run(self):
        t0 = self.core.get_rtio_counter_mu()
        i = 0
        while True:
            t = self.core.get_rtio_counter_mu()
            dt_s = (t-t0)
            if dt_s < 1e9:
                continue
            t0 = t
            core_log(i)
            i += 1