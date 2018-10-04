from migen import *
from hp_dma import *

def test(dut):
    yield from dut.addr_base.write(0x12340)
    yield from dut.n_bursts.write(3)

    for _ in range(5):
        yield

    yield dut.bus.ar.ready.eq(1)
    yield

    yield from dut.trigger.write(1)


    def deliver_read_word(w, last=False):
        yield dut.bus.r.data.eq(w)
        yield dut.bus.r.valid.eq(1)
        if last:
            yield dut.bus.r.last.eq(1)
        for _ in range(100):
            yield
            if (yield dut.bus.r.ready):
                yield dut.bus.r.valid.eq(0)
                yield dut.bus.r.last.eq(0)
                break

    yield
    N=(yield dut.bus.ar.len)+1

    for _ in range( (yield dut.n_bursts.storage)+1 ):
        for i in range(N):
            yield from deliver_read_word(2*i | (2*i+1)<<32, last=i==N-1)

        for _ in range(5):
            yield

    for _ in range(10):
        yield


if __name__ == "__main__":
    dut = HP_DMA_READ()

    run_simulation(dut, test(dut), vcd_name="test.vcd",  clocks={"sys": 8})
