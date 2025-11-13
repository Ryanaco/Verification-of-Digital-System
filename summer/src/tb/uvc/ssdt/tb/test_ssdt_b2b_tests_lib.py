""" Test library for the SSDT-UVC B2B.
"""


import pyuvm
from pyuvm import uvm_factory
from cocotb.triggers import RisingEdge
from uvc.ssdt.tb.ssdt_b2b_base_test import ssdt_b2b_base_test
from uvc.ssdt.tb.ssdt_b2b_sequence_lib import *


# Default values
_TIMEOUT_TIME = 1000
_TIMEOUT_UNIT = 'ns'


# ---------------------------------------------------------------------------------------------
# Base test setup.
# ---------------------------------------------------------------------------------------------
class test_ssdt_b2b_base_setup(ssdt_b2b_base_test):
    """ Base test class.
    0. Reset all input signals.
    1. Wait 1clk cycle.
    2. Reset for 2clk cycles.
    3. Wait 1clk cycle.
    4. Start 10 sequences.
    """

    def __init__(self, name="test_ssdt_b2b_base_test", parent=None):

        super().__init__(name, parent)

    async def run_phase(self):

        await super().run_phase()

        # Clean inputs
        self.dut.in_data.value = 0
        self.dut.in_valid.value = 0

        self.logger.debug(f"Resetting DUT...")

        await RisingEdge(self.dut.clk)
        self.dut.rst.value = 1

        await RisingEdge(self.dut.clk)
        await RisingEdge(self.dut.clk)
        self.dut.rst.value = 0

        self.logger.debug(f"Resetting DONE.")


# ---------------------------------------------------------------------------------------------
# Test running default sequence. (bringup_test)
# ---------------------------------------------------------------------------------------------
@pyuvm.test(timeout_time=_TIMEOUT_TIME, timeout_unit=_TIMEOUT_UNIT)
class test_ssdt_b2b_default_seq(test_ssdt_b2b_base_setup):
    """ Test running default sequence for the SSDT-UVC.
    """

    def __init__(self, name="test_ssdt_b2b_default_seq", parent=None):

        super().__init__(name, parent)

    async def run_phase(self):

        self.logger.info(f"{'-'*30} Running test <{self.get_name()}> {'-'*30}")

        self.raise_objection()

        await super().run_phase()

        # Start sequences
        for _ in range(0,5):

            # Start sequence
            await (self.virt_sequence.start(self.tb_env_ssdt_b2b.virtual_sequencer))

        self.drop_objection()

        self.logger.info(f"{'-'*30} END 'run_phase' of <{self.__class__.__name__}> {'-'*30}")

