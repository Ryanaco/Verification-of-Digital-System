# -------------------------------------------------------------------------------
# NOT COCOTB ARGS
# -------------------------------------------------------------------------------

ROOT_DIR = $(shell pwd)

# Defining path
RTL_VERSION := rtl
RTL_DIR = $(ROOT_DIR)/../$(RTL_VERSION)

TB_DIR = $(ROOT_DIR)

TB_TESTS_DIR = $(ROOT_DIR)/tests

# ALl test modules, for regression testing
TB_TEST_PATHS = $(wildcard tests/cl_marb_*_test.py)
TB_TEST_LIST = $(patsubst tests/%.py, %, $(TB_TEST_PATHS))

REF_MODEL_SOURCEDIR := $(ROOT_DIR)/ref_model
REF_MODEL_BUILDDIR := $(REF_MODEL_SOURCEDIR)/_build

# Make dir if does not exist
$(shell mkdir -p $(REF_MODEL_BUILDDIR))

# because Makefile is in a different directory
export PYTHONPATH := $(TB_DIR):$(TB_TESTS_DIR)

LOCAL_PYTHON_BIN := $(shell which python)
PYTHON_PREFIX := $(shell $(LOCAL_PYTHON_BIN) -c "import sys; print(sys.base_prefix)")
PYTHON_VERSION := $(shell $(LOCAL_PYTHON_BIN) -c "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')")

export PYTHON_H_HOME = $(PYTHON_PREFIX)/include/$(PYTHON_VERSION)
export PYTHON_LIB = $(VIRTUAL_ENV)/lib/$(PYTHON_VERSION)/:$(REF_MODEL_BUILDDIR):$(TB_TESTS_DIR)

export PYUVM_LOG_LEVEL := INFO

# ------------------------------------------------------------------------------
# COCOTB ARGS
# ------------------------------------------------------------------------------

# Defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
# Verilog source files to include
VERILOG_INCLUDE_DIRS := $(RTL_DIR)
VERILOG_SOURCES := $(RTL_DIR)/pkg_mem_arb_types.sv
VERILOG_SOURCES += $(RTL_DIR)/apb_config_if.sv
VERILOG_SOURCES += $(RTL_DIR)/priority_sel.sv
VERILOG_SOURCES += $(RTL_DIR)/single_sort.sv
VERILOG_SOURCES += $(RTL_DIR)/mem_arb.sv
VERILOG_SOURCES += $(RTL_DIR)/mem_arb_wrapper.sv

# TOPLEVEL is the DUT wrapper
TOPLEVEL := mem_arb_wrapper

# RTL Parameters
ADDR_WIDTH ?= 8
DATA_WIDTH ?= 8

COMPILE_ARGS += -P$(TOPLEVEL).ADDR_WIDTH=$(ADDR_WIDTH)
COMPILE_ARGS += -P$(TOPLEVEL).DATA_WIDTH=$(DATA_WIDTH)

# MODULE is the basename of the Python test file
MODULE   := tests.cl_marb_basic_test

# Move the results generated inside the sim_build directory
COCOTB_RESULTS_FILE = $(shell pwd)/$(SIM_BUILD)/results.xml

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim

# ------------------------------------------------------------------------------

# To run our targets and cocotb targets
clean::
	@$(MAKE) local-clean -C $(TB_DIR)

# ------------------------------------------------------------------------------
# Because of Reference Model
# ------------------------------------------------------------------------------

# Compiler
CC := gcc

# Flags for compilation (adding warnings are always good)
CFLAGS = -g -Wall --debug

# Source files
REF_MODEL_SOURCES = $(REF_MODEL_SOURCEDIR)/ref_model_wrapper.c \
					$(REF_MODEL_SOURCEDIR)/ref_model.c \
					$(REF_MODEL_SOURCEDIR)/ref_model.h

ifeq ($(PYUVM_LOG_LEVEL), DEBUG)
    $(info PYUVM_LOG_LEVEL is ${PYUVM_LOG_LEVEL})
endif

# ------------------------------------------------------------------------------
# Simulation targets
# ------------------------------------------------------------------------------


# -------------------------------------------------------------------------------
# Because of PyVSC and coverage
# -------------------------------------------------------------------------------

# PyVSC (help debug)
export VSC_SOLVEFAIL_DEBUG = 0
export VSC_CAPTURE_SRCINFO = 0
export VSC_DEBUG = 0

THE_SIM_BUILD = $(TB_DIR)/$(SIM_BUILD)
COV_FILES = $(shell find $(THE_SIM_BUILD) -type f \( -iname "*.xml" \))

# https://pyucis.readthedocs.io/en/latest/commands.html
.PHONY: coverage-merge
coverage-merge:
	@echo ""
	@echo "======================================================"
	@echo "Merging coverage files..."
	@echo $(THE_SIM_BUILD)
	@echo $(COV_FILES)
	@echo "======================================================"
	@echo ""
	@$(VIRTUAL_ENV)/bin/pyucis merge --out $(THE_SIM_BUILD)/merge_cov.xml $(THE_SIM_BUILD)/*.xml

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

# -------------------------------------------------------------------------------
# Clean-up target
# -------------------------------------------------------------------------------

.PHONY: local-clean
local-clean:
	@echo -e "\n------------------ Internal cleanup --------------------\n"
	# Remove build stuff from ref. model
	@rm -fv $(shell find $(REF_MODEL_SOURCEDIR) -type f \( -iname "*.*o" \);)
	# Remove all __pycache__ folders
	@rm -fvr $(shell find $(ROOT_DIR) -type d \( -iname '__pycache__' \);)

.PHONY: local-debug
local-debug::
	@echo -e "\n--------------------------------------\n"
	@echo DEBUG_MODE = $(DEBUG_MODE)

	@echo TB_TEST_LIST = $(TB_TEST_LIST)

	@echo SOURCES = $(REF_MODEL_SOURCES)
	@echo SOURCEDIR = $(REF_MODEL_SOURCEDIR)
	@echo BUILDDIR = $(REF_MODEL_BUILDDIR)

	@echo PYTHONPATH = $(PYTHONPATH)
	@echo PYTHON_H_HOME = $(PYTHON_H_HOME)
	@echo "run 'where python' "
	@echo -e "\n--------------------------------------\n"
