TOPLEVEL_LANG ?= verilog

PWD=$(shell pwd)

export PYTHONPATH := $(PWD)/../ref_model:$(PYTHONPATH)

VERILOG_SOURCES = $(PWD)/../rtl/adder.sv

TOPLEVEL := adder
MODULE   := test_adder

include $(shell cocotb-config --makefiles)/Makefile.sim

clean::
	@$(MAKE) local-clean -C $(PWD)

.PHONY: local-clean
local-clean:
	@echo -e "\n------------------ Internal cleanup --------------------\n"
	# Remove all __pycache__ folders
	@rm -fvr $(shell find $(ROOT_DIR) -type d \( -iname '__pycache__' \);)
	@rm -rf $(PWD)/../ref_model/__pycache__
# Remove results.xml
	@rm -fr $(shell find $(ROOT_DIR) -name results.xml)
