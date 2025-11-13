# Defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Defining path
PWD=$(shell pwd)

# Adding all Verilog sources
VERILOG_SOURCES += $(PWD)/../rtl/parallel.sv

# TOPLEVEL is the name of the toplevel module in the Verilog file(s)
TOPLEVEL := parallel

# MODULE is the basename of the Python test file
MODULE   := <your_test_name>

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim

clean::
	@$(MAKE) local-clean -C $(PWD)

.PHONY: local-clean
local-clean:
	@echo -e "\n------------------ Internal cleanup --------------------\n"
	# Remove all __pycache__ folders
	@rm -fvr $(shell find $(ROOT_DIR) -type d \( -iname '__pycache__' \);)
	# Remove results.xml
	@rm -fr $(shell find $(ROOT_DIR) -name results.xml)
