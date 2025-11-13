import pyuvm
from pyuvm import *
from cocotb.triggers import ClockCycles

from cl_marb_tb_base_test import cl_marb_tb_base_test
from vseqs.cl_reg_simple_seq import cl_reg_simple_seq
from vseqs.cl_marb_basic_seq import cl_marb_basic_seq
from uvc.sdt.src import *

@pyuvm.test(timeout_time = 1000, timeout_unit = 'ns')
class cl_marb_basic_test(cl_marb_tb_base_test):
    """Basic test - running WR and RD on each producer"""

    def __init__(self, name = "cl_marb_basic_test", parent = None):
        super().__init__(name, parent)

    async def run_phase(self):
        self.logger.info("Start run_phase() -> MARB basic test")
        self.raise_objection()

        await super().run_phase()

        # Register sequence for enabling and configuring the Memory Arbiter sequence
        conf_seq = cl_reg_simple_seq.create("conf_seq")
        conf_seq.randomize()

        cocotb.start_soon(conf_seq.start(self.marb_tb_env.virtual_sequencer))

        self.top_seq = cl_marb_basic_seq.create("top_seq")
        await self.top_seq.start(self.marb_tb_env.virtual_sequencer)

        await ClockCycles(self.dut.clk, 20)
        self.drop_objection()

        self.logger.info("End run_phase() -> MARB basic test")

