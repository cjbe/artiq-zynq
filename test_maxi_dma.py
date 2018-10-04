from migen import *
from maxi_dma import *



def test_basic(dut):
    yield from dut.engine.addr_base.write(0x12340)

    for _ in range(5):
        yield

    yield dut.engine.bus.ar.ready.eq(1)
    yield

    yield dut.trigger.eq(1)

    while True:
        if (yield dut.engine.bus.ar.valid):
            break
        yield
    yield dut.engine.bus.ar.ready.eq(0)
    yield dut.trigger.eq(0)

    def deliver_read_word(w, last=False):
        yield dut.engine.bus.r.data.eq(w)
        yield dut.engine.bus.r.valid.eq(1)
        if last:
            yield dut.engine.bus.r.last.eq(1)
        for _ in range(100):
            yield
            if (yield dut.engine.bus.r.ready):
                yield dut.engine.bus.r.valid.eq(0)
                yield dut.engine.bus.r.last.eq(0)
                break

    yield
    for i in range(4):
        yield from deliver_read_word(2*i | (2*i+1)<<32, last=i==3)

    for _ in range(5):
        yield

    while True:
        if (yield dut.engine.bus.aw.valid):
            break
        yield
    yield dut.engine.bus.aw.ready.eq(1)
    yield
    yield dut.engine.bus.aw.ready.eq(0)

    yield dut.engine.bus.w.ready.eq(1)
    
    for _ in range(10):
        yield


class Wrapper(Module):
    def __init__(self):
        self.trigger = Signal()

        self.submodules.engine = MAXI_DMA(trigger_stb=self.trigger)
        self.submodules.dma_test = DMA_Test(self.engine)


if __name__ == "__main__":
    dut = Wrapper()

    run_simulation(dut, test_basic(dut), vcd_name="test.vcd",  clocks={"sys": 8})
