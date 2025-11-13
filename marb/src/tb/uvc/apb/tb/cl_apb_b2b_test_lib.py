import pyuvm
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from random import randint

from uvc.apb.tb.cl_apb_b2b_base_test import cl_apb_b2b_base_test
from uvc.apb.tb.cl_apb_b2b_seq_lib import *
from uvc.apb.src import *


@pyuvm.test()
class cl_apb_b2b_simple_test(cl_apb_b2b_base_test):
    """Simple B2B test, running 1 sequence"""
    def __init__(self, name = "cl_apb_b2b_simple_test", parent = None):
        super().__init__(name, parent)

    def start_of_simulation_phase(self):
        self.logger.info("Start start_of_simulation_phase() -> APB TB simple test")
        super().start_of_simulation_phase()
        uvm_factory().set_type_override_by_type(cl_apb_b2b_base_seq, cl_apb_b2b_single_seq)
        self.logger.info("End start_of_simulation_phase() -> APB TB simple test")

@pyuvm.test(skip=False)
class cl_apb_b2b_random_test(cl_apb_b2b_base_test):
    """Random B2B test, running 100 random sequences"""
    def __init__(self, name = "cl_apb_b2b_random_test", parent = None):
        super().__init__(name, parent)

    def start_of_simulation_phase(self):
        self.logger.info("Start start_of_simulation_phase() -> APB TB random test")
        super().start_of_simulation_phase()
        uvm_factory().set_type_override_by_type(cl_apb_b2b_base_seq, cl_apb_b2b_random_seq)
        self.logger.info("End start_of_simulation_phase() -> APB TB random test")


@pyuvm.test(skip=False)
class cl_apb_b2b_zd_test(cl_apb_b2b_base_test):
    """ B2B test, running 100 random sequences with no delay"""
    def __init__(self, name = "cl_apb_b2b_zd_test", parent = None):
        super().__init__(name, parent)

    def start_of_simulation_phase(self):
        self.logger.info("Start start_of_simulation_phase() -> APB TB zd test")
        super().start_of_simulation_phase()
        uvm_factory().set_type_override_by_type(cl_apb_b2b_base_seq, cl_apb_b2b_zd_seq)
        self.logger.info("End start_of_simulation_phase() -> APB TB zd test")


@pyuvm.test(skip=False)
class cl_apb_b2b_reset_test(cl_apb_b2b_base_test):
    """B2B Test, testing default active low reset.
    Running 100 random sequences and activating reset concurrently at random"""
    def __init__(self, name = "cl_apb_b2b_reset_test", parent = None):
        super().__init__(name, parent)

    async def run_phase(self):
        self.logger.info("Start run_phase() -> APB TB reset test")
        self.raise_objection()

        await self.trigger_reset()
        cocotb.start_soon(self.apb_if_checkers.check_assertions())
        cocotb.start_soon(self.data_integrity_check_RD())
        cocotb.start_soon(self.data_integrity_check_WR())

        self.logger.debug("Start b2b sequence as top")
        self.top_seq = cl_apb_b2b_random_seq.create("top_seq")

        # Starting top sequnce task and reset task in parallel
        reset_task = cocotb.start_soon(self.activate_reset_cont())
        await self.top_seq.start(self.apb_b2b_env.virtual_sequencer)

        # Stop reset task, wait additional runtime to finish sequence
        reset_task.kill()
        await ClockCycles(self.apb_if.clk, 2)

        self.drop_objection()

        self.logger.info("End run_phase() -> APB TB reset test")

    async def activate_reset_cont(self):
        """Continuously activation of reset at random interval"""
        while True:
            await ClockCycles(self.apb_if.clk,randint(2, 98))

            # Activate reset
            self.apb_if.rst.value = 0
            await ClockCycles(self.apb_if.clk, randint(1, 20))
            # Deactivate reset
            self.apb_if.rst.value = 1


@pyuvm.test(skip=False)
class cl_apb_b2b_reset_high_test(cl_apb_b2b_reset_test):
    """B2B Test, testing active high reset, as apb_cfg.active_low_reset = False.
    Running 100 random sequences and activating reset concurrently at random"""
    def __init__(self, name = "cl_apb_b2b_reset_high_test", parent = None):
        super().__init__(name, parent)

    def build_phase(self):
        super().build_phase()

        self.cfg.apb_producer_cfg.active_low_reset = False
        self.cfg.apb_consumer_cfg.active_low_reset = False

    async def activate_reset_cont(self):
        """Continuously activation of reset at random interval"""
        while True:
            await ClockCycles(self.apb_if.clk,randint(2, 98))

            # Activate reset
            self.apb_if.rst.value = 1
            await ClockCycles(self.apb_if.clk, randint(1, 20))
            # Deactivate reset
            self.apb_if.rst.value = 0

    async def trigger_reset(self):
        """Activation and deactivation of reset (active high)"""

        self.clk_period = randint(1,5)
        cocotb.start_soon(Clock(self.apb_if.clk, self.clk_period,'ns').start())
        self.logger.info("B2BTB: waiting for reset")

        await ClockCycles(self.apb_if.clk, randint(0, 5))
        # Activate reset
        self.apb_if.rst.value = 1
        await ClockCycles(self.apb_if.clk, randint(1, 20))

        # Deactivate reset
        self.apb_if.rst.value = 0

        self.logger.info("B2BTB: Reset Done")
