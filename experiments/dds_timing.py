from artiq.experiment import *
import numpy as np

class Benchmark(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.dds = self.get_device("urukul0_ch0")

    @kernel
    def bisect_underflow(self, f, t_max_mu=1000, t_min_mu=0):
        t = 0
        while (t_max_mu-t_min_mu) > 2:
            t = np.int64( (t_max_mu+t_min_mu)/2 )
            print(np.int32(t_min_mu), np.int32(t_max_mu))
            try:
                f(t)
            except RTIOUnderflow:
                print("Underflow")
                if t == t_max_mu:
                    raise ValueError("Upper bound underflowed")
                t_min_mu = t
            else:
                t_max_mu = t
        return t

    @kernel
    def dds_update_rate(self):
        t=0
        def f(t):
            self.core.reset()
            for i in range(1000):
                with parallel:
                    delay_mu(t)
                    self.dds.set(80*MHz, amplitude=0.1, phase=0.5)
        t = self.bisect_underflow(lambda t: f(t), t_max_mu=50000)
        print("Sustained DDS update time: ", np.int32(t), "mu")

    @kernel
    def dds_setmu_update_rate(self):
        t=0

        def f(t):
            f_mu = self.dds.frequency_to_ftw(80*MHz)
            amp_mu = self.dds.amplitude_to_asf(0.1)
            phase_mu = self.dds.turns_to_pow(0.5)
            self.core.reset()
            for i in range(1000):
                with parallel:
                    delay_mu(t)
                    self.dds.set_mu(f_mu, asf=amp_mu, pow=phase_mu)
        t = self.bisect_underflow(lambda t: f(t), t_max_mu=50000)
        print("Sustained DDS set_mu update time: ", np.int32(t), "mu")

    @kernel
    def measure_dds_timeline_advance(self):
        self.core.break_realtime()
        t0 = now_mu()
        self.dds.set(80*MHz, amplitude=0.1, phase=0.5)
        dt = now_mu()-t0
        core_log("DDS timeline advance:", np.int32(dt), "mu")

    @kernel
    def run(self):
        self.core.reset()
        self.dds.cpld.init(blind=True)
        self.dds.init(blind=True)

        # self.measure_dds_timeline_advance()
        self.dds_update_rate()
        # self.dds_setmu_update_rate()
