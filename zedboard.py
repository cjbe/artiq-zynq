from migen_axi.integration.soc_core import SoCCore
from migen_axi.platforms import zedboard
from migen import *
from misoc.interconnect.csr import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from migen.genlib.cdc import MultiReg

from misoc.integration.builder import *

from artiq.gateware import rtio
from artiq.gateware.rtio.phy import ttl_simple, ttl_serdes_7series, spi2
from artiq.gateware import eem

from artiq.gateware.rtio.phy import ttl_serdes_7series, ttl_simple
from artiq.gateware import fmcdio_vhdci_eem

from maxi_dma import MAXI_DMA, DMA_KernelInitiator, DMA_Test
from hp_dma import HP_DMA_READ
from operator import attrgetter

import argparse
import os


class _RTIOCRG(Module, AutoCSR):
    def __init__(self):
        self._pll_reset = CSRStorage(reset=1)
        self._pll_locked = CSRStatus()
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_rtio = ClockDomain()
        # self.clock_domains.cd_rtiox4 = ClockDomain(reset_less=True)

        pll_locked = Signal()
        rtio_clk = Signal()
        rtiox4_clk = Signal()
        self.specials += [
            Instance("PLLE2_ADV",
                     p_STARTUP_WAIT="FALSE", o_LOCKED=pll_locked,

                     p_REF_JITTER1=0.24,
                     p_CLKIN1_PERIOD=8.0, p_CLKIN2_PERIOD=8.0,
                     i_CLKIN2=self.cd_sys.clk,
                     # Warning: CLKINSEL=0 means CLKIN2 is selected
                     i_CLKINSEL=0,

                     # VCO @ 1GHz when using 125MHz input
                     p_CLKFBOUT_MULT=8, p_DIVCLK_DIVIDE=1,
                     i_CLKFBIN=self.cd_rtio.clk,
                     i_RST=self._pll_reset.storage,

                     o_CLKFBOUT=rtio_clk,

                     # p_CLKOUT0_DIVIDE=2, p_CLKOUT0_PHASE=0.0,
                     # o_CLKOUT0=rtiox4_clk
                     ),
            Instance("BUFG", i_I=rtio_clk, o_O=self.cd_rtio.clk),
            # Instance("BUFG", i_I=rtiox4_clk, o_O=self.cd_rtiox4.clk),

            AsyncResetSynchronizer(self.cd_rtio, ~pll_locked),
            MultiReg(pll_locked, self._pll_locked.status)
        ]


def fix_serdes_timing_path(platform):
    # ignore timing of path from OSERDESE2 through the pad to ISERDESE2
    platform.add_platform_command(
        "set_false_path -quiet "
        "-through [get_pins -filter {{REF_PIN_NAME == OQ || REF_PIN_NAME == TQ}} "
            "-of [get_cells -filter {{REF_NAME == OSERDESE2}}]] "
        "-to [get_pins -filter {{REF_PIN_NAME == D}} "
            "-of [get_cells -filter {{REF_NAME == ISERDESE2}}]]"
    )



class Zedboard(SoCCore):
    def __init__(self):
        plat = zedboard.Platform()
        super().__init__(platform=plat)

        fclk0 = self.ps7.fclk.clk[0]
        self.clock_domains.cd_sys = ClockDomain()
        self.specials += Instance("BUFG", i_I=fclk0, o_O=self.cd_sys.clk),
        plat.add_platform_command("create_clock -name clk_fpga_0 -period 8 [get_pins \"PS7/FCLKCLK[0]\"]")
        plat.add_platform_command("set_input_jitter clk_fpga_0 0.24")

        self.evento_stb = Signal()
        evento_latched = Signal()
        evento_latched_d = Signal()
        self.sync += evento_latched.eq(self.ps7.event.o)
        self.sync += evento_latched_d.eq(evento_latched)
        self.comb += self.evento_stb.eq(evento_latched != evento_latched_d)

        self.submodules.hp_dma = HP_DMA_READ(bus=self.ps7.s_axi_hp0)
        self.csr_devices.append("hp_dma")

        # Debug ports
        # pads_b = plat.request("pmod",1)
        # ar, aw, w, r, b = attrgetter("ar", "aw", "w", "r", "b")(self.dma.bus)
        # self.comb += pads_b[0].eq(self.dma.trigger_stb)

        plat.add_extension(fmcdio_vhdci_eem.io)
        plat.add_connectors(fmcdio_vhdci_eem.connectors)

        self.rtio_channels = []

        for i in range(4):
            pad = plat.request("user_led", i)
            phy = ttl_simple.InOut(pad)
            self.submodules += phy
            self.rtio_channels.append(rtio.Channel.from_phy(phy))

        for i in range(4):
            led = plat.request("user_led", i+4)
            s = Signal()
            btn = plat.request("user_btn", i)
            self.comb += led.eq(s | btn)
            self.comb += s.eq(self.ps7.gpio.o[i])

        pads = plat.request("pmod",0)
        for i in range(8):
            phy = ttl_simple.InOut(pads[i])
            self.submodules += phy
            self.rtio_channels.append(rtio.Channel.from_phy(phy))

        ttl_phy = ttl_simple.Output
        eem.Urukul.add_std(self, 0, 1, ttl_phy, iostandard="LVDS_25")
        eem.Urukul.add_std(self, 2, 3, ttl_phy, iostandard="LVDS_25")

        self.add_rtio(self.rtio_channels)


    def add_rtio(self, rtio_channels):
        self.submodules.rtio_crg = _RTIOCRG()
        self.csr_devices.append("rtio_crg")

        self.submodules.rtio_core = rtio.Core(rtio_channels)
        self.csr_devices.append("rtio_core")
        self.submodules.rtio = rtio.KernelInitiator()
        self.csr_devices.append("rtio")

        self.submodules.dma = MAXI_DMA(bus=self.ps7.s_axi_acp,
                                        user=self.ps7.s_axi_acp_user,
                                        trigger_stb=self.evento_stb)
        self.csr_devices.append("dma")
        self.submodules.rtio_dma = DMA_KernelInitiator(engine=self.dma)

        self.submodules.cri_con = rtio.CRIInterconnectShared(
            [self.rtio.cri, self.rtio_dma.cri],
            [self.rtio_core.cri])
        self.csr_devices.append("cri_con")

        self.platform.add_false_path_constraints(
            self.rtio_crg.cd_rtio.clk)

        self.comb += self.rtio_crg.cd_sys.clk.eq(self.cd_sys.clk)




def main():
    parser = argparse.ArgumentParser()
    builder_args(parser)
    args = parser.parse_args()

    soc = Zedboard()

    builder = Builder(soc, **builder_argdict(args))
    builder.software_packages = []
    root_path = os.path.dirname(os.path.abspath(__file__))
    builder.add_software_package("libm")
    builder.add_software_package("libprintf")
    builder.add_software_package("libunwind")
    builder.add_software_package("libbase")
    builder.add_software_package("runtime", os.path.join(root_path, "firmware/runtime"))
    builder.build()


if __name__ == "__main__":
    main()
