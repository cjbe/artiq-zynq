from artiq.experiment import *


class Minimal(EnvExperiment):
    def build(self):
        self.setattr_device("core")

    @kernel
    def run(self):
        core_log(" :: Hello from kernel")
        # try:
        raise ValueError
        # except ValueError as e:
        #     core_log(" :: Caught exception.")
