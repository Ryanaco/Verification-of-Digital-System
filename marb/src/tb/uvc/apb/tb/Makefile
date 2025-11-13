# Defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Defining path
PWD=$(shell pwd)

# setting the python path to marb/src/tb
export PYTHONPATH = $(PWD)/../../../

# Adding all SystemVerilog sources
VERILOG_SOURCES = apb_b2b_tb_dut.sv

# TOPLEVEL is the name of the toplevel module in the Verilog file(s)
TOPLEVEL := toplevel

# RTL Parameters
ADDR_WIDTH ?= 32
DATA_WIDTH ?= 32

COMPILE_ARGS += -P$(TOPLEVEL).ADDR_WIDTH=$(ADDR_WIDTH)
COMPILE_ARGS += -P$(TOPLEVEL).DATA_WIDTH=$(DATA_WIDTH)

# MODULE is the basename of the Python test file
MODULE   := cl_apb_b2b_test_lib

# Move the results generated inside the sim_build directory
COCOTB_RESULTS_FILE = $(shell pwd)/$(SIM_BUILD)/results.xml

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
