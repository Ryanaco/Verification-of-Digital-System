import pyuvm
from cocotb.triggers import ClockCycles
from random import randint

from cl_sdt_b2b_base_test import cl_sdt_b2b_base_test
from cl_sdt_b2b_seq_lib import *
from uvc.sdt.src import *


@pyuvm.test()
class cl_sdt_b2b_simple_test(cl_sdt_b2b_base_test):
    """Simple B2B test, running 1 sequence with rd = 1, addr = 1 and data = 2"""
    def __init__(self, name = "cl_sdt_b2b_simple_test", parent = None):
        super().__init__(name, parent)

    def start_of_simulation_phase(self):
        self.logger.info("Start start_of_simulation_phase() -> SDT TB simple test")
        super().start_of_simulation_phase()
        uvm_factory().set_type_override_by_type(cl_sdt_b2b_base_seq, cl_sdt_b2b_single_seq)
        self.logger.info("End start_of_simulation_phase() -> SDT TB simple test")

@pyuvm.test()
class cl_sdt_b2b_random_test(cl_sdt_b2b_base_test):
    """Random B2B test, running 100 random sequences"""
    def __init__(self, name = "cl_sdt_b2b_random_test", parent = None):
        super().__init__(name, parent)

    def start_of_simulation_phase(self):
        self.logger.info("Start start_of_simulation_phase() -> SDT TB random test")
        super().start_of_simulation_phase()
        uvm_factory().set_type_override_by_type(cl_sdt_b2b_base_seq, cl_sdt_b2b_random_seq)
        self.logger.info("End start_of_simulation_phase() -> SDT TB random test")


@pyuvm.test()
class cl_sdt_b2b_test(cl_sdt_b2b_base_test):
    """ B2B test, running 100 random sequences with no delay"""
    def __init__(self, name = "cl_sdt_b2b_test", parent = None):
        super().__init__(name, parent)

    def start_of_simulation_phase(self):
        self.logger.info("Start start_of_simulation_phase() -> SDT TB b2b test")
        super().start_of_simulation_phase()
        uvm_factory().set_type_override_by_type(cl_sdt_b2b_base_seq, cl_sdt_b2b_seq)
        self.logger.info("End start_of_simulation_phase() -> SDT TB b2b test")


@pyuvm.test()
class cl_sdt_b2b_reset_test(cl_sdt_b2b_base_test):
    def __init__(self, name = "cl_sdt_b2b_reset_test2", parent = None):
        super().__init__(name, parent)

    async def run_phase(self):
        self.logger.info("Start run_phase() -> SDT TB reset test")
        self.raise_objection()

        await self.trigger_reset()
        cocotb.start_soon(self.assert_check.check_assertions())
        cocotb.start_soon(self.data_integrity_check_RD())
        cocotb.start_soon(self.data_integrity_check_WR())

        self.logger.debug("Start b2b sequence as top")
        self.top_seq = cl_sdt_b2b_seq.create("top_seq")

        # Starting top sequnce task and reset task in parallel
        reset_task = cocotb.start_soon(self.activate_reset_cont())
        await self.top_seq.start(self.sdt_b2b_env.virtual_sequencer)

        # Stop reset task, wait additional runtime to finish sequence
        reset_task.kill()
        await ClockCycles(self.sdt_if.clk, 2)

        self.drop_objection()

        self.logger.info("End run_phase() -> SDT TB reset test")

    async def activate_reset_cont(self):
        """Continuously activation of reset at random interval"""
        while True:
            await ClockCycles(self.sdt_if.clk,randint(2, 98))

            # Activate reset
            self.sdt_if.rst.value = 1
            await ClockCycles(self.sdt_if.clk, randint(1, 20))
            # Deactivate reset
            self.sdt_if.rst.value = 0