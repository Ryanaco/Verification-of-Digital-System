#
# Simple cocotb test.
#

import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock


@cocotb.test()
async def sat_filter_default_test(dut):
    """ Test sets input data values once.
    """

    # Create a 2ns period clock on port clk
    clock = Clock(dut.clk, 2, units="ns")
    # Start the clock
    cocotb.start_soon(clock.start())

    # Reset input values
    dut.in_data.value = 0
    dut.in_valid.value = 0

    # Reset device
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0

    await RisingEdge(dut.clk)

    # Set values to the input
    dut.in_data.value = 15
    dut.in_valid.value = 1

    await ClockCycles(dut.clk, 1)

    # Reset input values
    dut.in_data.value = 0
    dut.in_valid.value = 0

    # Wait some time before ending test
    await ClockCycles(dut.clk, 2)