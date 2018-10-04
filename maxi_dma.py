from migen import *
from migen_axi.interconnect import axi
from misoc.interconnect.csr import *
from artiq.gateware import rtio
from operator import attrgetter


class MAXI_DMA(Module, AutoCSR):
    def __init__(self, bus=None, user=None, trigger_stb=None):
        self.bus = bus or axi.Interface(data_width=64)

        self.addr_base = CSRStorage(32)
        self.trig_count = CSRStatus(32)
        self.write_count = CSRStatus(32)

        # Dout : Data received from CPU, output by DMA module
        # Din : Data driven into DMA module, written into CPU
        # When stb assert, index shows word being read/written, dout/din holds
        # data
        #
        # Cycle:
        # trigger_stb pulsed at start
        # Then out_burst_len words are strobed out of dout
        # Then, when din_ready is high, in_burst_len words are strobed in to din
        self.dout_stb = Signal()
        self.din_stb = Signal()
        self.dout_index = Signal(max=16)
        self.din_index = Signal(max=16)
        self.din_ready = Signal()
        self.dout = Signal(64)
        self.din = Signal(64)

        self.out_burst_len = Signal(max=16)
        self.in_burst_len = Signal(max=16)

        ###
        self.trigger_stb = trigger_stb

        self.sync += If(trigger_stb, self.trig_count.status.eq(self.trig_count.status+1))

        if user:
            self.comb += user.aruser.eq(0x1f)
            self.comb += user.awuser.eq(0x1f)

        ar, aw, w, r, b = attrgetter("ar", "aw", "w", "r", "b")(self.bus)

        ### Read
        self.comb += [
            ar.addr.eq(self.addr_base.storage),
            self.dout.eq(r.data),
            r.ready.eq(1),
            ar.burst.eq(axi.Burst.incr.value),
            ar.len.eq(self.out_burst_len-1), # Number of transfers in burst (0->1 transfer, 1->2 transfers...)
            ar.size.eq(3), # Width of burst: 3 = 8 bytes = 64 bits
            ar.cache.eq(0xf),
        ]

        # read control
        self.submodules.read_fsm = read_fsm = FSM(reset_state="IDLE")
        read_fsm.act("IDLE",
            If(trigger_stb,
                ar.valid.eq(1),
                If(ar.ready,
                    NextState("READ")
                ).Else(
                    NextState("READ_START")
                )
            )
        )
        read_fsm.act("READ_START",
            ar.valid.eq(1),
            If(ar.ready,
                NextState("READ"),
            )
        )
        read_fsm.act("READ",
            ar.valid.eq(0),
            If(r.last & r.valid,
                NextState("IDLE")
            )
        )

        self.sync += [
            If(read_fsm.ongoing("IDLE"),
                self.dout_index.eq(0)
            ).Else(If(r.valid & read_fsm.ongoing("READ"),
                    self.dout_index.eq(self.dout_index+1)
                )
            )
        ]

        self.comb += self.dout_stb.eq(r.valid & r.ready)

        ### Write
        self.comb += [
            w.data.eq(self.din),
            aw.addr.eq(self.addr_base.storage+32), # Write to next cache line
            w.strb.eq(0xff),
            aw.burst.eq(axi.Burst.incr.value),
            aw.len.eq(self.in_burst_len-1), # Number of transfers in burst minus 1
            aw.size.eq(3), # Width of burst: 3 = 8 bytes = 64 bits
            aw.cache.eq(0xf),
            b.ready.eq(1),
        ]

        # write control
        self.submodules.write_fsm = write_fsm = FSM(reset_state="IDLE")
        write_fsm.act("IDLE",
            w.valid.eq(0),
            aw.valid.eq(0),
            If(trigger_stb,
                aw.valid.eq(1),
                If(aw.ready, # assumes aw.ready is not randomly deasserted
                    NextState("DATA_WAIT")
                ).Else(
                    NextState("AW_READY_WAIT")
                )
            )
        )
        write_fsm.act("AW_READY_WAIT",
            aw.valid.eq(1),
            If(aw.ready,
                NextState("DATA_WAIT"),
            )
        )
        write_fsm.act("DATA_WAIT",
            aw.valid.eq(0),
            If(self.din_ready,
                w.valid.eq(1),
                NextState("WRITE")
            )
        )
        write_fsm.act("WRITE",
            w.valid.eq(1),
            If(w.ready & w.last,
                NextState("IDLE")
            )
        )

        self.sync += If(w.ready & w.valid, self.write_count.status.eq(self.write_count.status+1))

        self.sync += [
            If(write_fsm.ongoing("IDLE"),
                self.din_index.eq(0)
            ),
            If(w.ready & w.valid, self.din_index.eq(self.din_index+1))
        ]

        self.comb += [
            w.last.eq(0),
            If(self.din_index==aw.len, w.last.eq(1))
        ]

        self.comb += self.din_stb.eq(w.valid & w.ready)


class DMA_Test(Module):
    def __init__(self, engine=None):
        if engine is None:
            engine = MAXI_DMA()

        N = 4

        regs = [Signal(64) for _ in range(N)]

        self.comb += [
            engine.out_burst_len.eq(N),
            engine.in_burst_len.eq(N),
        ]

        self.sync += [
            If(engine.trigger_stb, engine.din_ready.eq(0)),
            If(engine.dout_stb & (engine.dout_index==3), engine.din_ready.eq(1))
        ]

        dout_cases = {}
        for i in range(N):
            dout_cases[i] = regs[i].eq(engine.dout)

        din_cases = {}
        for i in range(N):
            din_cases[i] = engine.din.eq(regs[i])

        self.sync += [
            If(engine.dout_stb,
                Case(engine.dout_index, dout_cases)
            ),
        ]

        self.comb += [
            If(engine.din_stb,
                Case(engine.din_index, din_cases)
            )
        ]


class DMA_KernelInitiator(Module):
    def __init__(self, engine=None, cri=None):
        self.engine = engine or MAXI_DMA()
        self.cri = cri or rtio.cri.Interface()

        ###
        cri = self.cri

        self.comb += [
            engine.out_burst_len.eq(4),
            engine.in_burst_len.eq(4),
        ]

        cmd = Signal(8)
        cmd_write = Signal()
        cmd_read = Signal()
        self.comb += [
            cmd_write.eq(cmd==0),
            cmd_read.eq(cmd==1)
        ]


        dout_cases = {}
        dout_lw = Signal(32)
        dout_hw = Signal(32)
        self.comb += [
            dout_lw.eq(engine.dout[:32]),
            dout_hw.eq(engine.dout[32:])
        ]
        dout_cases[0] = [
            cmd.eq(dout_lw[24:]),
            cri.chan_sel.eq(dout_lw[:24]),
            cri.o_address.eq(dout_hw[:16])
        ]
        dout_cases[1] = [
            cri.timestamp.eq(engine.dout)
        ]
        dout_cases[2] = [cri.o_data.eq(engine.dout)] # only lowest 64 bits

        self.sync += [
            cri.cmd.eq(rtio.cri.commands["nop"]),
            If(engine.dout_stb,
                Case(engine.dout_index, dout_cases),
                If(engine.dout_index==2,
                    If(cmd_write, cri.cmd.eq(rtio.cri.commands["write"])),
                    If(cmd_read, cri.cmd.eq(rtio.cri.commands["read"]))
                )
            )
        ]

        # If input event, wait for response before allow input data to be
        # sampled
        # TODO: If output, wait for wait flag clear
        RTIO_I_STATUS_WAIT_STATUS = 4
        RTIO_O_STATUS_WAIT = 1

        self.submodules.fsm = fsm = FSM(reset_state="IDLE")

        fsm.act("IDLE",
            If(engine.trigger_stb, NextState("WAIT_OUT_CYCLE"))
        )
        fsm.act("WAIT_OUT_CYCLE",
            engine.din_ready.eq(0),
            If(engine.dout_stb & (engine.dout_index==3),
                NextState("WAIT_READY")
            )
        )
        fsm.act("WAIT_READY",
            If(cmd_read & (cri.i_status & RTIO_I_STATUS_WAIT_STATUS == 0) \
                | cmd_write & ~(cri.o_status & RTIO_O_STATUS_WAIT),
                engine.din_ready.eq(1),
                NextState("IDLE")
            )
        )

        din_cases_cmdwrite = {
            0: [engine.din.eq((1<<16) | cri.o_status)],
            1: [engine.din.eq(0)],
        }
        din_cases_cmdread = {
            0: [engine.din[:32].eq((1<<16) | cri.i_status), engine.din[32:].eq(cri.i_data)],
            1: [engine.din.eq(cri.i_timestamp)]
        }

        self.comb += [
            If(cmd_read, Case(engine.din_index, din_cases_cmdread)),
            If(cmd_write, Case(engine.din_index, din_cases_cmdwrite)),
        ]
