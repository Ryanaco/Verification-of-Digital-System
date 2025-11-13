""" SDT-UVC base test.
- pyUVM testcase.
- Base test file to be used as parent."""

from pyuvm import *
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from cocotb.queue import Queue
from random import randint
import vsc
import os, warnings

from cl_sdt_b2b_config import cl_sdt_b2b_config
from cl_sdt_b2b_seq_lib import *
from cl_sdt_b2b_env import cl_sdt_b2b_env
from uvc.sdt.src import *

_LOG_LEVELS = ["DEBUG", "CRITICAL", "ERROR", "WARNING", "INFO", "NOTSET", "NullHandler"]

class cl_sdt_b2b_base_test(uvm_test):
    def __init__(self, name = "cl_sdt_b2b_base_test", parent = None):
        # ----------------------------------------------------------------------
        if os.getenv("PYUVM_LOG_LEVEL") in _LOG_LEVELS:
            _PYUVM_LOG_LEVEL = os.getenv('PYUVM_LOG_LEVEL')
        else:
            _PYUVM_LOG_LEVEL = "INFO"
            if os.getenv("PYUVM_LOG_LEVEL") != None:
                uvm_root().logger.warning(f"{'='*50}\n   Wrong value for 'PYUVM_LOG_LEVEL' in Makefile. Changing to default value: 'INFO'.\n    {'='*50}")

        uvm_report_object.set_default_logging_level(_PYUVM_LOG_LEVEL)
        # ----------------------------------------------------------------------

        super().__init__(name, parent)

        self.sdt_if = None

        self.cfg = None
        self.sdt_b2b_env = None

        self.rd_data_queue = None
        self.wr_data_queue = None

        self.data_check_passed = True

        # Quick fix because of warnings og PYVSC
        warnings.simplefilter("ignore")

    def build_phase(self):
        self.logger.info("Start build_phase() -> SDT TB base test")
        super().build_phase()

        # Creating configuration object handle
        self.cfg = cl_sdt_b2b_config.create("cfg")

        # There are multiple instances
        self.cfg.sdt_producer_cfg.seq_item_override = SequenceItemOverride.USER_DEFINED
        self.cfg.sdt_consumer_cfg.seq_item_override = SequenceItemOverride.USER_DEFINED

        # Configure the ADDR_WIDTH and DATA_WIDTH
        self.cfg.sdt_producer_cfg.ADDR_WIDTH = int(cocotb.top.ADDR_WIDTH)
        self.cfg.sdt_producer_cfg.DATA_WIDTH = int(cocotb.top.DATA_WIDTH)

        self.cfg.sdt_consumer_cfg.ADDR_WIDTH  = int(cocotb.top.ADDR_WIDTH)
        self.cfg.sdt_consumer_cfg.DATA_WIDTH  = int(cocotb.top.DATA_WIDTH)

        # Configure the value of the rd_data signal when no ACK
        self.cfg.sdt_producer_cfg.rd_data_no_ack_value = "x"
        self.cfg.sdt_consumer_cfg.rd_data_no_ack_value = "x"

        # Creating interface, setting in configDB
        self.sdt_if = cl_sdt_interface(clk_signal = cocotb.top.clk, rst_signal = cocotb.top.rst)
        self.sdt_if._set_width_values(self.cfg.sdt_producer_cfg.ADDR_WIDTH, self.cfg.sdt_producer_cfg.DATA_WIDTH)

        # Pass virtual interfaces
        self.cfg.sdt_producer_cfg.vif = self.sdt_if
        self.cfg.sdt_consumer_cfg.vif = self.sdt_if

        # Assertions checker

        # Create TB env
        ConfigDB().set(self, 'sdt_b2b_env', 'sdt_if', self.sdt_if)
        ConfigDB().set(self, 'sdt_b2b_env', 'cfg', self.cfg)
        self.sdt_b2b_env = cl_sdt_b2b_env.create("sdt_b2b_env", self)

        # Data validations queues
        self.rd_data_queue = Queue(maxsize = 2)
        self.wr_data_queue = Queue(maxsize = 2)

        # Setting in ConfigDB
        ConfigDB().set(self, '*', 'rd_data_queue', self.rd_data_queue)
        ConfigDB().set(self, '*', 'wr_data_queue', self.wr_data_queue)

        self.logger.info("End build_phase() -> SDT TB base test")

        # Instance factory overrides to insert the correct ADDR_WIDTH and DATA_WIDTH
        uvm_factory().set_inst_override_by_type(cl_sdt_seq_item, sdt_change_width(self.cfg.sdt_producer_cfg.ADDR_WIDTH, self.cfg.sdt_producer_cfg.DATA_WIDTH), "*sdt_producer*")
        uvm_factory().set_inst_override_by_type(cl_sdt_seq_item, sdt_change_width(self.cfg.sdt_consumer_cfg.ADDR_WIDTH, self.cfg.sdt_consumer_cfg.DATA_WIDTH), "*sdt_consumer*")

    def connect_phase(self):
        self.logger.info("Start connect_phase() -> SDT TB base test")
        super().connect_phase()
        self.sdt_if.connect(rd_signal      = cocotb.top.rd,
                            wr_signal      = cocotb.top.wr,
                            addr_signal    = cocotb.top.addr,
                            wr_data_signal = cocotb.top.wr_data,
                            rd_data_signal = cocotb.top.rd_data,
                            ack_signal     = cocotb.top.ack)

        self.logger.info("End connect_phase() -> SDT TB base test")

    async def run_phase(self):
        self.logger.info("Start run_phase() -> SDT TB base test")
        self.raise_objection()
        await super().run_phase()

        await self.trigger_reset()

        # Start assertions and data integrity check
        cocotb.start_soon(self.data_integrity_check_RD())
        cocotb.start_soon(self.data_integrity_check_WR())

        # Starting top seq - should be overwritten in test
        self.top_seq = cl_sdt_b2b_base_seq.create("top_seq")
        await self.top_seq.start(self.sdt_b2b_env.virtual_sequencer)

        self.drop_objection()
        self.logger.info("End run_phase() -> SDT TB base test")

    async def trigger_reset(self):
        """Activation and deactivation of reset """
        self.clk_period = randint(1,5)
        cocotb.start_soon(Clock(self.sdt_if.clk, self.clk_period,'ns').start())
        self.logger.info("B2BTB: waiting for reset")

        await ClockCycles(self.sdt_if.clk, randint(0, 5))
        # Activate reset
        self.sdt_if.rst.value = 1
        await ClockCycles(self.sdt_if.clk, randint(1, 20))

        # Deactivate reset
        self.sdt_if.rst.value = 0

        self.logger.info("B2BTB: Reset Done")

    async def data_integrity_check_RD(self):
        """Comparing read data for data integrity check"""
        while True:
            while not self.rd_data_queue.full():
                await RisingEdge(cocotb.top.clk)
            send_data = self.rd_data_queue.get_nowait()
            received_data = self.rd_data_queue.get_nowait()

            if send_data == received_data:
                self.logger.info(f"Read data is identical: 0x{send_data:02x} == 0x{received_data:02x}")
            else:
                self.data_check_passed = False
                self.logger.critical(f"Read data NOT identical: 0x{send_data:02x} != 0x{received_data:02x}")

    async def data_integrity_check_WR(self):
        """Comparing WR data for data integrity check"""
        while True:
            while not self.wr_data_queue.full():
                await RisingEdge(cocotb.top.clk)
            send_data = self.wr_data_queue.get_nowait()
            received_data = self.wr_data_queue.get_nowait()

            if send_data == received_data:
                self.logger.debug(f"Write data is identical: 0x{send_data:02x} == 0x{received_data:02x}")
            else:
                self.data_check_passed = False
                self.logger.critical(f"Write data NOT identical: 0x{send_data:02x} != 0x{received_data:02x}")


    def report_phase(self):
        super().report_phase()
        assert self.data_check_passed, "data check failed"

        # Creating coverage report with PyVSC
        self.setup_pyvsc_coverage_report()

    def setup_pyvsc_coverage_report(self):

        # Writing coverage report in (.txt format)
        f = open(f'sim_build/{self.get_type_name()}_cov.txt', "w")
        f.write(f"Coverage report for {self.get_type_name()} \n")
        f.write("------------------------------------------------\n \n")
        vsc.report_coverage(fp=f, details=True)
        f.close()

        # Writing coverage report in XML-format
        # Destination for coverage data
        _SIM_BUILD_FOLDER_ = os.getenv("SIM_BUILD", default="sim_build")
        uvm_root().logger.debug(f"{'='*50}\n 'SIM_BUILD' is '{_SIM_BUILD_FOLDER_}'.\n    {'='*50}")

        filename = f'{_SIM_BUILD_FOLDER_}/{self.get_type_name()}_cov.xml'
        fmt = "xml"  # Format of the coverage data. ‘xml’ and ‘libucis’ supported
        # Path to a library implementing the UCIS C API (default=None)
        libucis = None

        vsc.write_coverage_db(
            filename,
            fmt,
            libucis
        )

        # For each file only information regarding the test will show
        vsc.impl.coverage_registry.CoverageRegistry.clear()
