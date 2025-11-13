# --------------------- NOT COCOTB ARGS --------------------------------------
ROOT_DIR = $(shell pwd)

# Defining paths
RTL_DIR = $(ROOT_DIR)/../rtl
TB_DIR = $(ROOT_DIR)

TB_TESTS_DIR = $(TB_DIR)/tests
# Get all file names from the test folder to be used in the MODULE arg
TB_TESTS_FILENAMES = $(shell find $(TB_TESTS_DIR) -type f \( -iname "test*.py" -or -iname "*test.py" \) -exec basename {} .py \; | paste -s -d ',')

TB_VSEQS_DIR = $(TB_DIR)/vseqs

SSDT_TESTS_DIR = $(TB_DIR)/uvc/ssdt/tb

# because Makefile is in a different directory
export PYTHONPATH = $(TB_DIR):$(TB_TESTS_DIR)

LOCAL_PYTHON_BIN := $(shell which python)
PYTHON_PREFIX := $(shell $(LOCAL_PYTHON_BIN) -c "import sys; print(sys.base_prefix)")
PYTHON_VERSION := $(shell $(LOCAL_PYTHON_BIN) -c "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')")

export PYTHON_H_HOME = $(PYTHON_PREFIX)/include/$(PYTHON_VERSION)
export PYTHON_LIB = $(VIRTUAL_ENV)/lib/$(PYTHON_VERSION)/:$(REF_MODEL_BUILDDIR):$(TB_TESTS_DIR)

export PYUVM_LOG_LEVEL := INFO

# --------------------- COCOTB ARGS --------------------------------------

# Defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL
COCOTB_LOG_LEVEL ?= INFO
export COCOTB_REDUCED_LOG_FMT = 1

# Verilog source files to include
VERILOG_INCLUDE_DIRS := $(RTL_DIR)
VERILOG_SOURCES := $(RTL_DIR)/summer.sv
VERILOG_SOURCES += $(RTL_DIR)/summer_wrapper.sv

# TOPLEVEL is the DUT instance
TOPLEVEL := summer_wrapper

# RTL Parameters
DATA_W ?= 4

COMPILE_ARGS += -P$(TOPLEVEL).DATA_W=$(DATA_W)

# MODULE is the basename of the Python test file
MODULE := $(TB_TESTS_FILENAMES)

# Move the results generated inside the sim_build directory
COCOTB_RESULTS_FILE = $(shell pwd)/$(SIM_BUILD)/results.xml

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim

# ------------------------------------------------------------------------------

# To run our targets and cocotb targets
debug: local-debug

clean::
	@$(MAKE) local-clean -C $(TB_DIR)
	rm -rf results.xml
	rm -rf .ipynb_checkpoints

# -------------------------------------------------------------------------------
# Because of PyVSC and coverage
# -------------------------------------------------------------------------------

# PyVSC (help debug)
export VSC_SOLVEFAIL_DEBUG = 0
export VSC_CAPTURE_SRCINFO = 0
export VSC_DEBUG = 0

THE_SIM_BUILD = $(TB_DIR)/$(SIM_BUILD)
COV_FILES = $(shell find $(THE_SIM_BUILD) -type f \( -iname "test_sat_filter*.xml" \))

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
	@$(VIRTUAL_ENV)/bin/pyucis merge --out $(THE_SIM_BUILD)/merge_cov.xml $(COV_FILES)

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
#
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

	@echo TB_TESTS_FILENAMES = $(TB_TESTS_FILENAMES)

	@echo SOURCES = $(REF_MODEL_SOURCES)
	@echo SOURCEDIR = $(REF_MODEL_SOURCEDIR)
	@echo BUILDDIR = $(REF_MODEL_BUILDDIR)

	@echo PYTHONPATH = $(PYTHONPATH)
	@echo PYTHON_H_HOME = $(PYTHON_H_HOME)
	@echo "run 'where python' "
	@echo -e "\n--------------------------------------\n"

.PHONY: local-help
local-help::
	@echo -e "\n--------------------------------------\n"
	@echo DEBUG_MODE = $(DEBUG_MODE)