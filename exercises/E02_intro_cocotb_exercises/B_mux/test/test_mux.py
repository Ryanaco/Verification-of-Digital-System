
import cocotb
from cocotb.triggers import RisingEdge

from cocotb.clock import Clock

@cocotb.test()
async def mux_basic_test(dut):
  """Test for out=A[1]"""
 
  # Start the clock as the mux RTL is clocked
  # NOTE: NO reset signal in the RTL
  clk = Clock(signal=dut.clk, period=2, units="ns")
  cocotb.start_soon(clk.start())


@cocotb.test()
async def mux_randomized_test(dut):
  """Test for randomizing out=A[sel]"""
 
  # Start the clock as the mux RTL is clocked
  # NOTE: NO reset signal in the RTL
  clk = Clock(signal=dut.clk, period=2, units="ns")
  cocotb.start_soon(clk.start())

