from artiq.experiment import *
import numpy as np

class Mandelbrot(EnvExperiment):
    def build(self):
        self.setattr_device("core")

    def col(self, i):
        sys.stdout.write(" .,-:;i+hHM$*#@ "[i])

    def row(self):
        print("")

    # based on: http://warp.povusers.org/MandScripts/python.html
    @kernel
    def run(self):
        minX = -2.0
        maxX = 1.0
        width = 78
        height = 36
        aspectRatio = 2

        yScale = (maxX-minX)*(height/width)*aspectRatio

        accum = 0.

        t0 = self.core.get_rtio_counter_mu()

        for y in range(height):
            for x in range(width):
                c_r = minX+x*(maxX-minX)/width
                c_i = y*yScale/height-yScale/2
                z_r = c_r
                z_i = c_i
                i = 0
                for i in range(16):
                    if z_r*z_r + z_i*z_i > 4:
                        break
                    new_z_r = (z_r*z_r)-(z_i*z_i) + c_r
                    z_i = 2*z_r*z_i + c_i
                    z_r = new_z_r
                accum += i

        dt = self.core.get_rtio_counter_mu() - t0
        core_log("Execution time:", np.int32(dt), "mu")
        # Takes 666763336 mu on Kasli