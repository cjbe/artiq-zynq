from migen import *
from migen_axi.interconnect import axi
from misoc.interconnect.csr import *
from operator import attrgetter


class HP_DMA_READ(Module, AutoCSR):
    def __init__(self, bus=None):
        self.bus = bus or axi.Interface(data_width=64)

        self.addr_base = CSRStorage(32)
        self.n_bursts = CSRStorage(32) # Number of bursts to do -1
        self.trigger = CSR(1)

        self.n_cycles = CSRStatus(32)
        self.status = CSRStatus(1)
        self.n_read = CSRStatus(32)

        self.dout = Signal(32)
        self.dout_stb = Signal()

        ###
        ar, aw, w, r, b = attrgetter("ar", "aw", "w", "r", "b")(self.bus)
        BURST_LEN = 16

        trigger_stb = self.trigger.re
        addr = Signal(32)
        read_request_accepted = Signal() # Asserted when the read request has been accepted
        read_request = Signal()
        n_done = Signal(32)

        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act("IDLE",
            If(trigger_stb,
                NextValue(addr, self.addr_base.storage),
                NextValue(read_request, 1),
                NextState("RUNNING")
            )
        )
        fsm.act("RUNNING",
            If(read_request_accepted,
                NextValue(addr, addr+BURST_LEN),
                NextValue(n_done, n_done+1),
                If(n_done == self.n_bursts.storage,
                    NextState("IDLE"),
                    NextValue(read_request, 0)
                )
            )
        )


        ### Read
        self.comb += [
            ar.addr.eq(self.addr_base.storage),
            self.dout.eq(r.data),
            r.ready.eq(1),
            ar.burst.eq(axi.Burst.incr.value),
            ar.len.eq(BURST_LEN-1), # Number of transfers in burst (0->1 transfer, 1->2 transfers...)
            ar.size.eq(3), # Width of burst: 3 = 8 bytes = 64 bits
            ar.cache.eq(0xf),
        ]

        # read control
        self.comb += read_request_accepted.eq(ar.ready & ar.valid)
        self.submodules.read_fsm = read_fsm = FSM(reset_state="IDLE")
        read_fsm.act("IDLE",
            If(read_request,
                ar.valid.eq(1),
                If(ar.ready,
                    NextState("WAIT")
                ).Else(
                    NextState("READ_START")
                )
            )
        )
        read_fsm.act("READ_START",
            ar.valid.eq(1),
            If(ar.ready,
                NextState("WAIT"),
            )
        )
        read_fsm.act("WAIT",
            NextState("IDLE")
        )

        self.comb += self.dout_stb.eq(r.valid & r.ready)

        n_bursts_received = Signal(32)
        self.sync += [
            If(trigger_stb, n_bursts_received.eq(0)),
            If(self.dout_stb & r.last, n_bursts_received.eq(n_bursts_received+1))
        ]

        self.sync += [
            If(trigger_stb, self.status.status.eq(1)),
            If(n_bursts_received==self.n_bursts.storage+1, self.status.status.eq(0))
        ]
        self.sync += [
            If(self.status.status, self.n_cycles.status.eq(self.n_cycles.status+1)),
            If(trigger_stb, self.n_cycles.status.eq(0))
        ]

        self.sync += [
            If(self.dout_stb, self.n_read.status.eq(self.n_read.status+1)),
            If(trigger_stb, self.n_read.status.eq(0))
        ]