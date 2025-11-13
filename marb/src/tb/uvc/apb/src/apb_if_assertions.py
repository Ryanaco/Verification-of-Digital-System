from pyuvm import *
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly
from cocotb.utils import get_sim_time

class if_apb_assert_check():
    def __init__(self, clk_signal, rst_signal):
        """Connecting the signals to the assertion class"""
        # General signals
        self.clk = clk_signal
        self.rst = rst_signal

        # Interface specific signals
        self.wr        = None
        self.sel       = None
        self.enable    = None
        self.addr      = None
        self.wdata     = None
        self.strb      = None
        self.rdata     = None
        self.ready     = None
        self.slverr    = None

        # Config
        self.cfg = None

        # Set as false if any assertion fail
        self.passed = True

    def connect(self):
        if self.cfg is None:
            raise UVMFatalError("APB CFG not set in APB assertion checker")

        self.wr        = self.cfg.vif.wr
        self.sel       = self.cfg.vif.sel
        self.enable    = self.cfg.vif.enable
        self.addr      = self.cfg.vif.addr
        self.wdata     = self.cfg.vif.wdata
        self.strb      = self.cfg.vif.strb
        self.rdata     = self.cfg.vif.rdata
        self.ready     = self.cfg.vif.ready
        self.slverr    = self.cfg.vif.slverr

    async def check_assertions(self):
        while True:
            # await deactivation of reset
            if self.cfg.active_low_reset:
                while self.rst.value == 0:
                    await RisingEdge(self.clk)
            else:
                while self.rst.value == 1:
                    await RisingEdge(self.clk)

            # start all assertions
            as_valid_sel    = cocotb.start_soon(self.valid_signal_always(self.sel, "sel"))
            as_valid_enable = cocotb.start_soon(self.valid_signal_always(self.enable, "enable"))
            as_valid_ready  = cocotb.start_soon(self.valid_signal_always(self.ready, "ready"))
            as_valid_addr   = cocotb.start_soon(self.valid_signal_when_sel(self.addr, "addr", self.cfg.ADDR_WIDTH))
            as_valid_op     = cocotb.start_soon(self.valid_signal_when_sel(self.wr, "wr", 1))
            as_valid_slverr = cocotb.start_soon(self.valid_slverr())
            as_valid_data   = cocotb.start_soon(self.valid_data())
            as_valid_rdata  = cocotb.start_soon(self.valid_rdata())

            as_stable_addr  = cocotb.start_soon(self.stable_signal_when_sel(self.addr, "addr"))
            as_stable_wdata = cocotb.start_soon(self.stable_signal_when_sel(self.wdata, "wdata"))
            as_stable_wr    = cocotb.start_soon(self.stable_signal_when_sel(self.wr, "wr"))
            as_stable_sel   = cocotb.start_soon(self.stable_sel())
            as_stable_strb  = cocotb.start_soon(self.stable_strb())

            as_no_enable            = cocotb.start_soon(self.no_enable())
            as_enable_life_cycle    = cocotb.start_soon(self.enable_life_cycle())

            # detecting asynchronous reset (active low or active high)
            if self.cfg.active_low_reset:
                await FallingEdge(self.rst)
            else:
                await RisingEdge(self.rst)

            # kill all assertions
            as_valid_sel.kill()
            as_valid_addr.kill()
            as_valid_enable.kill()
            as_valid_op.kill()
            as_valid_ready.kill()
            as_valid_slverr.kill()
            as_valid_data.kill()
            as_valid_rdata.kill()
            as_stable_addr.kill()
            as_stable_wdata.kill()
            as_stable_wr.kill()
            as_stable_sel.kill()
            as_stable_strb.kill()
            as_no_enable.kill()
            as_enable_life_cycle.kill()

    async def valid_signal_always(self, signal, signal_name):
        while True:
            # Wait 1 clk cycle
            await RisingEdge(self.clk)
            await ReadOnly()

            # <signal> must always be valid
            try:
                assert signal.value.binstr != 'x',\
                        f"APB ASSERTION ERROR ({round(get_sim_time('ns'))}ns): "\
                        f"{signal_name} must always be valid, was {signal.value.binstr}"
            except AssertionError as msg:
                self.passed = False
                print(msg)

    async def valid_signal_when_sel(self, signal, signal_name, signal_size):
        while True:
            # Wait 1 clk cycle
            await RisingEdge(self.clk)
            await ReadOnly()

            # If sel, then <signal> cannot be X
            try:
                if self.sel.value.binstr == '1' :
                    assert signal.value.binstr != 'x' * signal_size,\
                        f"APB ASSERTION ERROR ({round(get_sim_time('ns'))}ns): "\
                        f"when sel = 1: {signal_name} must be valid, was {signal.value.binstr}"
            except AssertionError as msg:
                self.passed = False
                print(msg)

    async def valid_slverr(self):
        while True:
            # Wait 1 clk cycle
            await RisingEdge(self.clk)
            await ReadOnly()

            # If sel & enable & ready, then slverr cannot be X
            try:
                if self.sel.value.binstr == '1' and self.enable.value.binstr == '1' and self.ready.value.binstr == '1':
                    assert self.slverr.value.binstr != 'x',\
                        f"APB ASSERTION ERROR ({round(get_sim_time('ns'))}ns): "\
                        f"when sel, enable & ready: slverr must be valid, "\
                        f"was {self.slverr.value.binstr}"
            except AssertionError as msg:
                self.passed = False
                print(msg)

    async def valid_rdata(self):
        while True:
            # Wait 1 clk cycle
            await RisingEdge(self.clk)
            await ReadOnly()

            # If sel & enable & ready & ~wr, then rdata cannot be X
            try:
                if (self.sel.value.binstr == '1' and self.enable.value.binstr == '1' and
                    self.ready.value.binstr == '1' and self.wr.value.binstr == '0'):
                    # when slverr = 1, the data can be invalid
                    if self.slverr.value.binstr == '0':
                        assert self.rdata.value.binstr != 'x' * self.cfg.DATA_WIDTH,\
                            f"APB ASSERTION ERROR ({round(get_sim_time('ns'))}ns): "\
                            f"when sel, enable & ready & ~wr: "\
                            f"rdata must be valid, was {self.rdata.value.binstr}"
            except AssertionError as msg:
                self.passed = False
                print(msg)

    async def valid_data(self):
        while True:
            # Wait 1 clk cycle
            await RisingEdge(self.clk)
            await ReadOnly()

            # If sel & wr & strb[i], then rdata cannot be X
            for i in range(self.cfg.STRB_WIDTH):
                try:
                    if self.sel.value.binstr == '1' and self.wr.value.binstr == '1' and self.strb.value.binstr[i] == '1':
                        assert self.wdata.value.binstr[8*i:8*i+7] != 'x' * 8,\
                            f"APB ASSERTION ERROR ({round(get_sim_time('ns'))}ns): "\
                            f"when sel, wr & strb[i]: wdata[8*i : 8*i+7] "\
                            f"must be valid, was {self.wdata.value.binstr}"
                except AssertionError as msg:
                    self.passed = False
                    print(msg)

    async def stable_signal_when_sel(self, signal, signal_name):
        while True:
            # Wait 1 clk cycle
            await RisingEdge(self.clk)
            await ReadOnly()

            # while sel , then <signal> must be stable
            try:
                if self.sel.value.binstr == '1':
                    prev_signal = signal.value.binstr

                    while self.sel.value.binstr == '1':
                        assert prev_signal == signal.value.binstr,\
                            f"APB ASSERTION ERROR ({round(get_sim_time('ns'))}ns): "\
                            f"while sel, then {signal_name} must be stable,"\
                            f"but changed from {prev_signal} to {signal.value.binstr}"

                        # Wait 1 clk cycle
                        await RisingEdge(self.clk)
                        await ReadOnly()
            except AssertionError as msg:
                self.passed = False
                print(msg)

    async def stable_sel(self):
        while True:
            # Wait 1 clk cycle
            await RisingEdge(self.clk)
            await ReadOnly()

            # when sel and enable, sel must remain stable until one clock cycle after ready
            try:
                if (self.sel.value.binstr == '1' and self.enable.value.binstr == '1' and
                       self.ready.value.binstr == '0'):
                    # Wait 1 clk cycle
                    await RisingEdge(self.clk)
                    await ReadOnly()

                    while (self.sel.value.binstr == '1' and self.enable.value.binstr == '1' and
                       self.ready.value.binstr == '0'):

                        assert self.sel.value.binstr == '1',\
                            f"APB ASSERTION ERROR ({round(get_sim_time('ns'))}ns): "\
                            f"when sel and enable, sel must remain stable until one clock cycle "\
                            f"after ready. Changed from 1 to {self.sel.value.binstr}"

                        # Wait 1 clk cycle
                        await RisingEdge(self.clk)
                        await ReadOnly()
            except AssertionError as msg:
                self.passed = False
                print(msg)

    async def stable_strb(self):
        while True:
            # Wait 1 clk cycle
            await RisingEdge(self.clk)
            await ReadOnly()

            # strb must be stable while sel and enable until ready
            try:
                if (self.sel.value.binstr == '1' and self.enable.value.binstr == '1' and
                       self.ready.value.binstr == '0'):
                    prev_strb = self.strb.value.binstr

                    # Wait 1 clk cycle
                    await RisingEdge(self.clk)
                    await ReadOnly()

                    while (self.sel.value.binstr == '1' and self.enable.value.binstr == '1' and
                       self.ready.value.binstr == '0'):

                        assert self.strb.value.binstr == prev_strb,\
                            f"APB ASSERTION ERROR ({round(get_sim_time('ns'))}ns): "\
                            f"strb must be stable while sel and enable until ready "\
                            f"changed from {prev_strb} to {self.strb.value.binstr}"

                        # Wait 1 clk cycle
                        await RisingEdge(self.clk)
                        await ReadOnly()

            except AssertionError as msg:
                self.passed = False
                print(msg)

    async def no_enable(self):
        while True:
            # Wait 1 clk cycle
            await RisingEdge(self.clk)
            await ReadOnly()

            # if ~sel then ~enable
            try:
                if self.sel.value.binstr == '0':
                    assert self.enable.value.binstr == '0',\
                            f"APB ASSERTION ERROR ({round(get_sim_time('ns'))}ns): "\
                            f"when ~sel then enable should be '0', but enable is '{self.enable.value.binstr}'"
            except AssertionError as msg:
                self.passed = False
                print(msg)

    async def enable_life_cycle(self):
        while True:
            # Wait 1 clk cycle
            await RisingEdge(self.clk)
            await ReadOnly()

            # one clock cycle after rising edge of sel, enable must remain high with sel
            try:
                if self.sel.value.binstr == '1':
                    assert self.enable.value.binstr == '0',\
                                f"APB ASSERTION ERROR ({round(get_sim_time('ns'))}ns): "\
                                f"enable must be 0 at rising edge of sel, but was enable={self.enable.value.binstr}"
                    # Wait 1 clk cycle
                    await RisingEdge(self.clk)
                    await ReadOnly()

                    while self.sel.value.binstr == '1':
                        assert self.enable.value.binstr == '1',\
                                f"APB ASSERTION ERROR ({round(get_sim_time('ns'))}ns): "\
                                f"enable must be 1 throughout sel, but was enable={self.enable.value.binstr}"
                        # Wait 1 clk cycle
                        await RisingEdge(self.clk)
                        await ReadOnly()
            except AssertionError as msg:
                self.passed = False
                print(msg)
