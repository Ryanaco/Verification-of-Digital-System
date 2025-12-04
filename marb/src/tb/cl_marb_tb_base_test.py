import os
import warnings
from random import randint

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer
from uvc.sdt.src.sdt_if_assertions import SDTProtocolChecker
import vsc
import pyuvm
from pyuvm import *
from cl_marb_ack_checker import MarbAckChecker

# -------------------------------------------------------
# Import UVC components
# -------------------------------------------------------
from uvc.apb.src import *          # apb_common, cl_apb_interface, ...
from uvc.sdt.src import *          # sdt_common, cl_sdt_interface, ...
from uvc.sdt.src.cl_sdt_config import cl_sdt_config

from cl_marb_tb_config import cl_marb_tb_config
from cl_marb_tb_env import cl_marb_tb_env

_LOG_LEVELS = ["DEBUG", "CRITICAL", "ERROR", "WARNING", "INFO", "NOTSET", "NullHandler"]


@pyuvm.test()
class cl_marb_tb_base_test(uvm_test):
    """A3 Base Test – Fully Implements A2 Environment"""

    def __init__(self, name="cl_marb_tb_base_test", parent=None):
        # Handle log level
        if os.getenv("PYUVM_LOG_LEVEL") in _LOG_LEVELS:
            _PYUVM_LOG_LEVEL = os.getenv("PYUVM_LOG_LEVEL")
        else:
            _PYUVM_LOG_LEVEL = "INFO"

        uvm_report_object.set_default_logging_level(_PYUVM_LOG_LEVEL)
        super().__init__(name, parent)

        self.dut = cocotb.top
        self.apb_if = None
        self.cfg = None
        self.marb_tb_env: cl_marb_tb_env | None = None

        warnings.simplefilter("ignore")

    # ============================================================
    # BUILD PHASE
    # ============================================================
    def build_phase(self):
        self.logger.info("Building MARB Base Test")
        super().build_phase()
        self.logger.critical(f"base_test loaded from: {__file__}")

        # Create the global configuration object
        self.cfg = cl_marb_tb_config("cfg")

        # ============== APB CONFIG ======================
        self.cfg.apb_cfg.driver = apb_common.DriverType.PRODUCER
        self.cfg.apb_cfg.seq_item_override = apb_common.SequenceItemOverride.USER_DEFINED
        self.cfg.apb_cfg.ADDR_WIDTH = 32
        self.cfg.apb_cfg.DATA_WIDTH = 32
        self.cfg.apb_cfg.STRB_WIDTH = 4
        self.cfg.apb_cfg.enable_masked_data = False
        self.cfg.apb_cfg.active_low_reset = False

        # Create APB interface and bind to DUT signals
        self.apb_if = cl_apb_interface(self.dut.clk, self.dut.rst)
        self.cfg.apb_cfg.vif = self.apb_if
        self.apb_if._set_width_parameters(
            self.cfg.apb_cfg.ADDR_WIDTH,
            self.cfg.apb_cfg.DATA_WIDTH
        )

        # ============== SDT CONFIG: 3 CIF + 1 MIF ===============
        SDT_ADDR_WIDTH = 8
        SDT_DATA_WIDTH = 8

        # Three CIF interfaces (Producers)
        self.cfg.sdt_cif_cfgs = []
        for i in range(3):
            cif_cfg = cl_sdt_config()
            cif_cfg.driver = sdt_common.DriverType.PRODUCER
            cif_cfg.ADDR_WIDTH = SDT_ADDR_WIDTH
            cif_cfg.DATA_WIDTH = SDT_DATA_WIDTH
            cif_cfg.vif = cl_sdt_interface(self.dut.clk, self.dut.rst, name=f"cif{i}")
            cif_cfg.vif._set_width_values(SDT_ADDR_WIDTH, SDT_DATA_WIDTH)
            self.cfg.sdt_cif_cfgs.append(cif_cfg)

        # One MIF interface (Consumer / memory)
        self.cfg.sdt_mif_cfg = cl_sdt_config()
        self.cfg.sdt_mif_cfg.driver = sdt_common.DriverType.CONSUMER
        self.cfg.sdt_mif_cfg.ADDR_WIDTH = SDT_ADDR_WIDTH
        self.cfg.sdt_mif_cfg.DATA_WIDTH = SDT_DATA_WIDTH
        self.cfg.sdt_mif_cfg.vif = cl_sdt_interface(self.dut.clk, self.dut.rst, name="mif")
        self.cfg.sdt_mif_cfg.vif._set_width_values(SDT_ADDR_WIDTH, SDT_DATA_WIDTH)

        # Pass config object into environment
        ConfigDB().set(self, "marb_tb_env", "cfg", self.cfg)
        self.marb_tb_env = cl_marb_tb_env("marb_tb_env", self)

        # Instantiate APB Agent
        try:
            from uvc.apb.src.cl_apb_agent import cl_apb_agent
            self.marb_tb_env.apb_agent = cl_apb_agent("apb_agent", self.marb_tb_env)
            ConfigDB().set(self, "marb_tb_env.apb_agent", "cfg", self.cfg.apb_cfg)
            self.logger.info("APB Agent successfully attached to MARB env")
        except Exception as e:
            self.logger.error(f"Failed to attach APB agent: {e}")

        self.logger.info("[BUILD] Finished build_phase()")

    # ============================================================
    # CONNECT PHASE
    # ============================================================
    def connect_phase(self):
        self.logger.info("[CONNECT] Starting connect_phase()")
        super().connect_phase()

        # Connect APB interface signals to DUT
        self.apb_if.connect(
            wr_signal=self.dut.conf_wr,
            sel_signal=self.dut.conf_sel,
            enable_signal=self.dut.conf_enable,
            addr_signal=self.dut.conf_addr,
            wdata_signal=self.dut.conf_wdata,
            strb_signal=self.dut.conf_strb,
            rdata_signal=self.dut.conf_rdata,
            ready_signal=self.dut.conf_ready,
            slverr_signal=self.dut.conf_slverr,
        )

        # ===== Connect SDT CIF and MIF interfaces to DUT =====

        # CIF0
        cif0 = self.cfg.sdt_cif_cfgs[0].vif
        cif0.rd      = self.dut.c0_rd
        cif0.wr      = self.dut.c0_wr
        cif0.addr    = self.dut.c0_addr
        cif0.wr_data = self.dut.c0_wr_data
        cif0.rd_data = self.dut.c0_rd_data
        cif0.ack     = self.dut.c0_ack

        # CIF1
        cif1 = self.cfg.sdt_cif_cfgs[1].vif
        cif1.rd      = self.dut.c1_rd
        cif1.wr      = self.dut.c1_wr
        cif1.addr    = self.dut.c1_addr
        cif1.wr_data = self.dut.c1_wr_data
        cif1.rd_data = self.dut.c1_rd_data
        cif1.ack     = self.dut.c1_ack

        # CIF2
        cif2 = self.cfg.sdt_cif_cfgs[2].vif
        cif2.rd      = self.dut.c2_rd
        cif2.wr      = self.dut.c2_wr
        cif2.addr    = self.dut.c2_addr
        cif2.wr_data = self.dut.c2_wr_data
        cif2.rd_data = self.dut.c2_rd_data
        cif2.ack     = self.dut.c2_ack

        # MIF
        mif = self.cfg.sdt_mif_cfg.vif
        mif.rd      = self.dut.m_rd
        mif.wr      = self.dut.m_wr
        mif.addr    = self.dut.m_addr
        mif.wr_data = self.dut.m_wr_data
        mif.rd_data = self.dut.m_rd_data
        mif.ack     = self.dut.m_ack

        self.logger.info("[CONNECT] Finished connect_phase()")

    # ============================================================
    # RUN PHASE
    # ============================================================
    async def run_phase(self):
        self.raise_objection()

        self.logger.critical("[A9] Starting MARB ACK Checker...")

        ack_checker = MarbAckChecker(
            "ack_checker",
            self.cfg.sdt_cif_cfgs[0].vif,
            self.cfg.sdt_cif_cfgs[1].vif,
            self.cfg.sdt_cif_cfgs[2].vif,
            self.cfg.sdt_mif_cfg.vif
        )

        cocotb.start_soon(ack_checker.start())
        self.logger.critical("[A9] ACK Checker started.")

        # Start clock and reset
        await self.start_clock()
        await self.trigger_reset()

        # A7: Start SDT protocol checkers
        self.logger.info("[A7] Creating SDT protocol checkers...")

        ck0 = SDTProtocolChecker("CIF0", self.cfg.sdt_cif_cfgs[0].vif)
        ck1 = SDTProtocolChecker("CIF1", self.cfg.sdt_cif_cfgs[1].vif)
        ck2 = SDTProtocolChecker("CIF2", self.cfg.sdt_cif_cfgs[2].vif)
        ckm = SDTProtocolChecker("MIF",  self.cfg.sdt_mif_cfg.vif)

        self.logger.info("[A7] SDTProtocolChecker objects created, starting tasks...")

        cocotb.start_soon(ck0.start())
        cocotb.start_soon(ck1.start())
        cocotb.start_soon(ck2.start())
        cocotb.start_soon(ckm.start())

        self.logger.info("[A7] SDT protocol checkers started.")

        await Timer(2000, units="ns")

        self.logger.info("[RUN] Completed MARB base test run_phase()")
        self.drop_objection()

    async def start_of_simulation_phase(self):
        await super().start_of_simulation_phase()

        self.logger.info("[A7] Starting SDT protocol checkers at start_of_simulation_phase()")

        ck0 = SDTProtocolChecker("CIF0", self.cfg.sdt_cif_cfgs[0].vif)
        ck1 = SDTProtocolChecker("CIF1", self.cfg.sdt_cif_cfgs[1].vif)
        ck2 = SDTProtocolChecker("CIF2", self.cfg.sdt_cif_cfgs[2].vif)
        ckm = SDTProtocolChecker("MIF", self.cfg.sdt_mif_cfg.vif)

        cocotb.start_soon(ck0.start())
        cocotb.start_soon(ck1.start())
        cocotb.start_soon(ck2.start())
        cocotb.start_soon(ckm.start())

        self.logger.info("SDT protocol checkers started.")

    async def start_clock(self):
        """Start DUT clock"""
        self.clk_period = randint(2, 5)
        self.logger.info(f"Starting clock (period={self.clk_period} ns)")
        cocotb.start_soon(Clock(self.dut.clk, self.clk_period, "ns").start())

    async def trigger_reset(self):
        """Apply reset signal"""
        await ClockCycles(self.dut.clk, randint(1, 3))
        self.logger.info("Applying reset...")
        self.dut.rst.value = 1
        await ClockCycles(self.dut.clk, randint(5, 10))
        self.dut.rst.value = 0
        self.logger.info("Reset complete")
