#
# Simple random cocotb test using random library.
#

import cocotb
import random

from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock



@cocotb.test()
async def sat_random_test(dut):
    """ Test sends 10 random inputs.
    """

    # Create a 2ns period clock on port clk
    clock = Clock(dut.clk, 2.5, units="ns")

    # Start the clock
    cocotb.start_soon(clock.start())

