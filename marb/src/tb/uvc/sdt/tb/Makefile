# -----------------------------------------------------------
# Makefile for the B2B TB.
# -----------------------------------------------------------

# --------------------- NOT COCOTB ARGS ----------------------------------

# Defining paths
TB_DIR = $(shell pwd)/../../../
SDT_SRC_DIR = $(shell pwd)/../src
SDT_TB_DIR = $(shell pwd)

# Python requirement
export PYTHONPATH := $(TB_DIR):$(SDT_TB_DIR):$(PYTHONPATH)

export PYUVM_LOG_LEVEL = INFO

# --------------------- COCOTB ARGS --------------------------------------

# Defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL
COCOTB_LOG_LEVEL ?= INFO

# Verilog source files to include
VERILOG_SOURCES := sdt_b2b_dut.sv

# TOPLEVEL is the DUT instance
TOPLEVEL := sdt_b2b

# RTL Parameters
COMPILE_ARGS += -P$(TOPLEVEL).ADDR_WIDTH=8
COMPILE_ARGS += -P$(TOPLEVEL).DATA_WIDTH=8

# MODULE is the basename of the Python test file
MODULE := cl_sdt_b2b_test_lib

# Move the results generated inside the sim_build directory
COCOTB_RESULTS_FILE = $(shell pwd)/$(SIM_BUILD)/results.xml

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim

# -----------------------------------------------------------
# PyVSC and coverage
# -----------------------------------------------------------

THE_SIM_BUILD = $(shell pwd)/$(SIM_BUILD)
COV_FILES = $(shell find $(THE_SIM_BUILD) -type f \( -iname "*.xml" \))

# Target that merges coverage files.
.PHONY: coverage-merge
coverage-merge: $(THE_SIM_BUILD)
	@echo ""
	@echo "======================================================"
	@echo "Merging coverage files..."
	@echo $(THE_SIM_BUILD)
	@echo $(COV_FILES)
	@echo "======================================================"
	@echo ""
	@$(VIRTUAL_ENV)/bin/pyucis merge --out $(THE_SIM_BUILD)/merge_cov.xml $(THE_SIM_BUILD)/*.xml

# Target that merges coverage files and opens PyUCIS-viewer.
.PHONY: coverage-view
coverage-view: coverage-merge
	@echo ""
	@echo "======================================================"
	@echo "Opening PyUCIS-viewer"
	@echo "======================================================"
	@echo ""
	@$(VIRTUAL_ENV)/bin/pyucis-viewer $(THE_SIM_BUILD)/merge_cov.xml

.PHONY: coverage
coverage: coverage-view