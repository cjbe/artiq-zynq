from artiq.experiment import *
import numpy as np

class TtlTests(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.ttlio = self.get_device("ttl0")

    @kernel
    def bisect_underflow(self, f, t_max_mu=1000, t_min_mu=0):
        t = 0
        while (t_max_mu-t_min_mu) > 1:
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
    def test_input_operation(self):
        core_log("")
        core_log("Test input operation ...")
        self.core.reset()
        self.ttlio.output()
        delay(10*us)
        with parallel:
            self.ttlio.gate_rising(10*us)
            with sequential:
                delay(1*us)
                t_out_mu = now_mu()
                self.ttlio.pulse(1*us)
        t_in_mu = self.ttlio.timestamp_mu()
        dt = np.int32(t_in_mu-t_out_mu)
        core_log("t_in-t_out:", dt, "mu")


    @kernel
    def event_response(self):
        """How soon after an input event can we reliably schedule an output event"""
        core_log("")
        core_log("Measuring minimum event response time")
        t = 0
        def f(t_delay):
            self.core.reset()

            self.ttlio.output()
            delay(1*us)
            for i in range(10):
                # Make sure we have plenty of slack
                delay(1000*us)
                self.ttlio.off()
                delay(1*us)
                with parallel:
                    self.ttlio.gate_rising(4*us)
                    with sequential:
                        delay(100*ns)
                        self.ttlio.pulse(100*ns)

                t_input = self.ttlio.timestamp_mu()
                at_mu(t_input+t_delay)
                self.ttlio.pulse(10*us)
        t = self.bisect_underflow(lambda t: f(t), t_max_mu=10000)
        core_log("Event response time: ", np.int32(t), "mu")

    @kernel
    def output_pulse_rate(self):
        """Sustained TTL output pulse rate"""
        core_log("")
        core_log("Measuring sustained output pulse rate")
        t=0
        def f(t):
            self.core.break_realtime()
            for i in range(20000):
                delay_mu(t)
                self.ttlio.pulse_mu(t)
        t = self.bisect_underflow(lambda t: f(t), t_max_mu=1000)
        core_log("Sustained pulse rate: ", np.int32(2*t), "mu")



    @kernel
    def run(self):
        self.core.reset()
        self.test_input_operation()
        self.output_pulse_rate()
        self.event_response()
