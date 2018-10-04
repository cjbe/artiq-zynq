from migen import *
from maxi_dma import *




def test(dut):
    def delay_cycles(N):
        for _ in range(N):
            yield

    yield from delay_cycles(4)

    yield dut.trigger_stb.eq(1)
    yield
    yield dut.trigger_stb.eq(0)

    yield from delay_cycles(2)

    assert (yield dut.din_ready)==0

    douts = [
        (0x2<<32) | (1<< 24) | 1, # address, cmd, channel
        0x55, # timestamp
        0x111111, # Data
        0x0
    ]

    yield dut.dout_stb.eq(1)
    for i in range( (yield dut.out_burst_len) ):
        yield dut.dout_index.eq(i)
        yield dut.dout.eq(douts[i])
        yield
    yield dut.dout_stb.eq(0)

    # yield dut.h.cri.o_status.eq(0x3)
    yield from delay_cycles(10)
    yield dut.h.cri.i_data.eq(1)
    yield dut.h.cri.i_timestamp.eq(2)
    yield dut.h.cri.i_status.eq(4)

    while True:
        if (yield dut.din_ready):
            break
        yield

    yield dut.din_stb.eq(1)
    print("Got: ")
    dins = []
    for i in range( (yield dut.in_burst_len) ):
        yield dut.din_index.eq(i)
        yield
        dins.append( (yield dut.din) )
    yield dut.din_stb.eq(0)
    print(dins)



class Wrapper(Module):
    def __init__(self):
        self.dout_stb = Signal()
        self.din_stb = Signal()
        self.dout_index = Signal(max=16)
        self.din_index = Signal(max=16)
        self.din_ready = Signal()
        self.dout = Signal(64)
        self.din = Signal(64)

        self.out_burst_len = Signal(max=16)
        self.in_burst_len = Signal(max=16)

        self.trigger_stb = Signal()

        self.submodules.h = DMA_KernelInitiator(self)


if __name__ == "__main__":
    dut = Wrapper()
    run_simulation(dut, test(dut), vcd_name="test_rtio_dma.vcd",  clocks={"sys": 8})
