""" APB-UVC base test.
- pyUVM testcase.
- Base test file to be used as parent."""

from pyuvm import *
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from cocotb.queue import Queue
from random import randint
import os, warnings
import vsc

from .cl_apb_b2b_config import cl_apb_b2b_config
from .cl_apb_b2b_seq_lib import *
from .cl_apb_b2b_env import cl_apb_b2b_env
from uvc.apb.src import *

_LOG_LEVELS = ["DEBUG", "CRITICAL", "ERROR", "WARNING", "INFO", "NOTSET", "NullHandler"]

class cl_apb_b2b_base_test(uvm_test):
    def __init__(self, name = "cl_apb_b2b_base_test", parent = None):
        super().__init__(name, parent)

        # ----------------------------------------------------------------------
        if os.getenv("PYUVM_LOG_LEVEL") in _LOG_LEVELS:
            _PYUVM_LOG_LEVEL = os.getenv('PYUVM_LOG_LEVEL')
        else:
            _PYUVM_LOG_LEVEL = "INFO"
            if os.getenv("PYUVM_LOG_LEVEL") != None:
                uvm_root().logger.warning(F"{'='*50}\n   Wrong value for 'PYUVM_LOG_LEVEL' in Makefile. Changing to default value: 'INFO'.\n    {'='*50}")

        uvm_report_object.set_default_logging_level(_PYUVM_LOG_LEVEL)
        # ----------------------------------------------------------------------

        self.apb_if = None

        self.cfg = None
        self.apb_b2b_env = None

        self.rd_data_queue = None
        self.wr_data_queue = None

        self.data_check_passed = True

        # Quick fix because of warnings og PYVSC
        warnings.simplefilter("ignore")

    def build_phase(self):
        self.logger.info("Start build_phase() -> APB TB base test")
        super().build_phase()

        # Creating configuration object handle
        self.cfg = cl_apb_b2b_config.create("cfg")

        # There are multiple instances
        self.cfg.apb_producer_cfg.seq_item_override = SequenceItemOverride.USER_DEFINED
        self.cfg.apb_consumer_cfg.seq_item_override = SequenceItemOverride.USER_DEFINED

        # Configure the ADDR_WIDTH, DATA_WIDTH and STRB_WIDTH
        self.cfg.apb_producer_cfg.set_width_parameters(int(cocotb.top.ADDR_WIDTH), int(cocotb.top.DATA_WIDTH))
        self.cfg.apb_consumer_cfg.set_width_parameters(int(cocotb.top.ADDR_WIDTH), int(cocotb.top.DATA_WIDTH))

        self.logger.info(f"ADDR WIDTH = {self.cfg.apb_producer_cfg.ADDR_WIDTH}, "
                         f"DATA WIDTH = {self.cfg.apb_producer_cfg.DATA_WIDTH}, "
                         f"STRB WIDTH = {self.cfg.apb_producer_cfg.STRB_WIDTH}")

        # Creating interface, setting in configDB
        self.apb_if = cl_apb_interface(clk_signal = cocotb.top.clk, rst_signal = cocotb.top.rst)
        self.apb_if._set_width_parameters(self.cfg.apb_producer_cfg.ADDR_WIDTH, self.cfg.apb_producer_cfg.DATA_WIDTH)

        # Pass virtual interfaces
        self.cfg.apb_producer_cfg.vif = self.apb_if
        self.cfg.apb_consumer_cfg.vif = self.apb_if

        # Create TB env
        ConfigDB().set(self, 'apb_b2b_env', 'cfg', self.cfg)
        self.apb_b2b_env = cl_apb_b2b_env.create("apb_b2b_env", self)

        # Data validations queues
        self.rd_data_queue = Queue(maxsize = 2)
        self.wr_data_queue = Queue(maxsize = 2)

        # Setting in ConfigDB
        ConfigDB().set(self, '*', 'rd_data_queue', self.rd_data_queue)
        ConfigDB().set(self, '*', 'wr_data_queue', self.wr_data_queue)

        # Instance factory overrides to insert the correct ADDR_WIDTH and DATA_WIDTH
        uvm_factory().set_inst_override_by_type(cl_apb_seq_item, apb_change_width(self.cfg.apb_producer_cfg.ADDR_WIDTH, self.cfg.apb_producer_cfg.DATA_WIDTH), "*apb_producer*")
        uvm_factory().set_inst_override_by_type(cl_apb_seq_item, apb_change_width(self.cfg.apb_consumer_cfg.ADDR_WIDTH, self.cfg.apb_consumer_cfg.DATA_WIDTH), "*apb_consumer*")

        self.apb_if_checkers = if_apb_assert_check(clk_signal       = cocotb.top.clk,
                                                   rst_signal       = cocotb.top.rst)
        self.apb_if_checkers.cfg = self.cfg.apb_producer_cfg

        self.logger.info("End build_phase() -> APB TB base test")

    def connect_phase(self):
        self.logger.info("Start connect_phase() -> APB TB base test")
        super().connect_phase()
        self.apb_if.connect(wr_signal       = cocotb.top.wr,
                            sel_signal      = cocotb.top.sel,
                            enable_signal   = cocotb.top.enable,
                            addr_signal     = cocotb.top.addr,
                            wdata_signal    = cocotb.top.wdata,
                            strb_signal     = cocotb.top.strb,
                            rdata_signal    = cocotb.top.rdata,
                            ready_signal    = cocotb.top.ready,
                            slverr_signal   = cocotb.top.slverr)

        self.apb_if_checkers.connect()

        self.logger.info("End connect_phase() -> APB TB base test")

    async def run_phase(self):
        self.logger.info("Start run_phase() -> APB TB base test")
        self.raise_objection()

        await super().run_phase()

        await self.trigger_reset()

        # Start assertions and data integrity check
        cocotb.start_soon(self.data_integrity_check_RD())
        cocotb.start_soon(self.data_integrity_check_WR())
        cocotb.start_soon(self.apb_if_checkers.check_assertions())

        # Starting top seq - should be overwritten in test
        self.top_seq = cl_apb_b2b_base_seq.create("top_seq")
        await self.top_seq.start(self.apb_b2b_env.virtual_sequencer)

        self.drop_objection()
        self.logger.info("End run_phase() -> APB TB base test")

    async def trigger_reset(self):
        """Activation and deactivation of reset """
        self.clk_period = randint(1,5)
        cocotb.start_soon(Clock(self.apb_if.clk, self.clk_period,'ns').start())
        self.logger.info("B2BTB: waiting for reset")

        await ClockCycles(self.apb_if.clk, randint(0, 5))
        # Activate reset
        self.apb_if.rst.value = 0
        await ClockCycles(self.apb_if.clk, randint(1, 20))

        # Deactivate reset
        self.apb_if.rst.value = 1

        self.logger.info("B2BTB: Reset Done")

    async def data_integrity_check_RD(self):
        """Comparing read data for data integrity check"""
        while True:
            while not self.rd_data_queue.full():
                await RisingEdge(cocotb.top.clk)
            send_data = self.rd_data_queue.get_nowait()
            received_data = self.rd_data_queue.get_nowait()

            if send_data == received_data:
                self.logger.debug(f"Read data is identical: {hex(send_data)} == {hex(received_data)}")
            else:
                self.data_check_passed = False
                self.logger.critical(f"Read data NOT identical: {hex(send_data)} != {hex(received_data)}")

    async def data_integrity_check_WR(self):
        """Comparing WR data for data integrity check"""
        while True:
            while not self.wr_data_queue.full():
                await RisingEdge(cocotb.top.clk)
            send_data = self.wr_data_queue.get_nowait()
            received_data = self.wr_data_queue.get_nowait()

            if send_data == received_data:
                self.logger.debug(f"Write data is identical: {hex(send_data)} == {hex(received_data)}")
            else:
                self.data_check_passed = False
                self.logger.critical(f"Write data NOT identical: {hex(send_data)} != {hex(received_data)}")


    def report_phase(self):
        super().report_phase()

        assert self.apb_if_checkers.passed, "assertions failed"

        assert self.data_check_passed, "data check failed"

        print(f"==== COVERAGE FOR TEST \"{type(self).__name__}\" ====")
        # vsc.report_coverage(details = True)
        vsc.write_coverage_db(f"sim_build/{type(self).__name__}_cov.xml")
        vsc.impl.coverage_registry.CoverageRegistry.clear()