import os
import warnings
from random import randint

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from uvc.sdt.src.sdt_if_assertions import SDTProtocolChecker
import vsc
import pyuvm
from pyuvm import *

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
        self.logger.info("🚧 Building MARB Base Test")
        super().build_phase()
        self.logger.critical(f"🔥 base_test loaded from file: {__file__}")
        # -------------- 创建总 config 对象 ----------------
        self.cfg = cl_marb_tb_config("cfg")

        # ============== APB CONFIG =======================
        self.cfg.apb_cfg.driver = apb_common.DriverType.PRODUCER
        self.cfg.apb_cfg.seq_item_override = apb_common.SequenceItemOverride.USER_DEFINED
        self.cfg.apb_cfg.ADDR_WIDTH = 32
        self.cfg.apb_cfg.DATA_WIDTH = 32
        self.cfg.apb_cfg.STRB_WIDTH = 4
        self.cfg.apb_cfg.enable_masked_data = False
        self.cfg.apb_cfg.active_low_reset = False

        # --- 创建 APB interface，并绑定到 DUT 时钟、复位 ---
        self.apb_if = cl_apb_interface(self.dut.clk, self.dut.rst)
        self.cfg.apb_cfg.vif = self.apb_if
        self.apb_if._set_width_parameters(
            self.cfg.apb_cfg.ADDR_WIDTH,
            self.cfg.apb_cfg.DATA_WIDTH
        )

        # ============== SDT CONFIG: 3 CIF + 1 MIF ==========
        # 和 mem_arb_wrapper 参数保持一致
        SDT_ADDR_WIDTH = 8
        SDT_DATA_WIDTH = 8

        # 3 个客户端 CIF：Producer
        self.cfg.sdt_cif_cfgs = []
        for i in range(3):
            cif_cfg = cl_sdt_config()
            cif_cfg.driver = sdt_common.DriverType.PRODUCER
            cif_cfg.ADDR_WIDTH = SDT_ADDR_WIDTH
            cif_cfg.DATA_WIDTH = SDT_DATA_WIDTH
            # name 用于 cl_sdt_interface 内部区分不同端口
            cif_cfg.vif = cl_sdt_interface(self.dut.clk, self.dut.rst, name=f"cif{i}")
            # ✅ 为 VIF 设置宽度参数
            cif_cfg.vif._set_width_values(SDT_ADDR_WIDTH, SDT_DATA_WIDTH)
            self.cfg.sdt_cif_cfgs.append(cif_cfg)

        # 1 个 MIF：Consumer（内存）
        self.cfg.sdt_mif_cfg = cl_sdt_config()
        self.cfg.sdt_mif_cfg.driver = sdt_common.DriverType.CONSUMER
        self.cfg.sdt_mif_cfg.ADDR_WIDTH = SDT_ADDR_WIDTH
        self.cfg.sdt_mif_cfg.DATA_WIDTH = SDT_DATA_WIDTH
        self.cfg.sdt_mif_cfg.vif = cl_sdt_interface(self.dut.clk, self.dut.rst, name="mif")
        # ✅ 为 VIF 设置宽度参数
        self.cfg.sdt_mif_cfg.vif._set_width_values(SDT_ADDR_WIDTH, SDT_DATA_WIDTH)

        # ============== 把总 config 放进 Env ================
        ConfigDB().set(self, "marb_tb_env", "cfg", self.cfg)
        self.marb_tb_env = cl_marb_tb_env("marb_tb_env", self)

        # ============== 实例化 APB Agent 并挂到 Env =========
        try:
            from uvc.apb.src.cl_apb_agent import cl_apb_agent
            self.marb_tb_env.apb_agent = cl_apb_agent("apb_agent", self.marb_tb_env)
            ConfigDB().set(self, "marb_tb_env.apb_agent", "cfg", self.cfg.apb_cfg)
            self.logger.info("🔗 APB Agent successfully attached to MARB env")
        except Exception as e:
            self.logger.error(f"❌ Failed to attach APB agent: {e}")

        self.logger.info("✅ [BUILD] Finished build_phase()")

    # ============================================================
    # CONNECT PHASE
    # ============================================================
    def connect_phase(self):
        self.logger.info("🔗 [CONNECT] Starting connect_phase()")
        super().connect_phase()

        # --- 连接 APB 接口信号到 DUT ---
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

        # =====================================================
        # 连接 SDT CIF / MIF 接口到 DUT —— 完整正确版本
        # =====================================================

        # ---------------- CIF0 ----------------
        cif0_vif = self.cfg.sdt_cif_cfgs[0].vif
        cif0_vif.rd      = self.dut.c0_rd
        cif0_vif.wr      = self.dut.c0_wr
        cif0_vif.addr    = self.dut.c0_addr
        cif0_vif.wr_data = self.dut.c0_wr_data
        cif0_vif.rd_data = self.dut.c0_rd_data
        cif0_vif.ack     = self.dut.c0_ack

        # ---------------- CIF1 ----------------
        cif1_vif = self.cfg.sdt_cif_cfgs[1].vif
        cif1_vif.rd      = self.dut.c1_rd
        cif1_vif.wr      = self.dut.c1_wr
        cif1_vif.addr    = self.dut.c1_addr
        cif1_vif.wr_data = self.dut.c1_wr_data
        cif1_vif.rd_data = self.dut.c1_rd_data
        cif1_vif.ack     = self.dut.c1_ack

        # ---------------- CIF2 ----------------
        cif2_vif = self.cfg.sdt_cif_cfgs[2].vif
        cif2_vif.rd      = self.dut.c2_rd
        cif2_vif.wr      = self.dut.c2_wr
        cif2_vif.addr    = self.dut.c2_addr
        cif2_vif.wr_data = self.dut.c2_wr_data
        cif2_vif.rd_data = self.dut.c2_rd_data
        cif2_vif.ack     = self.dut.c2_ack

        # ---------------- MIF（Memory） ----------------
        mif_vif = self.cfg.sdt_mif_cfg.vif
        mif_vif.rd      = self.dut.m_rd
        mif_vif.wr      = self.dut.m_wr
        mif_vif.addr    = self.dut.m_addr
        mif_vif.wr_data = self.dut.m_wr_data
        mif_vif.rd_data = self.dut.m_rd_data
        mif_vif.ack     = self.dut.m_ack

        self.logger.info("✅ [CONNECT] Finished connect_phase()")

    # ============================================================
    # START OF SIMULATION PHASE
    # ============================================================
    def start_of_simulation_phase(self):
        """A7: Initialize SDT Protocol Checkers in start_of_simulation_phase"""
        super().start_of_simulation_phase()

        self.logger.critical("🔍 [A7] NOW starting SDT protocol checker creation...")

        ck0 = SDTProtocolChecker("CIF0", self.cfg.sdt_cif_cfgs[0].vif)
        ck1 = SDTProtocolChecker("CIF1", self.cfg.sdt_cif_cfgs[1].vif)
        ck2 = SDTProtocolChecker("CIF2", self.cfg.sdt_cif_cfgs[2].vif)
        ckm = SDTProtocolChecker("MIF", self.cfg.sdt_mif_cfg.vif)

        self.logger.critical("✅ [A7] SDTProtocolChecker objects created, starting coroutines...")

        cocotb.start_soon(ck0.start())
        cocotb.start_soon(ck1.start())
        cocotb.start_soon(ck2.start())
        cocotb.start_soon(ckm.start())

        self.logger.critical("✅ [A7] SDT protocol checkers started.")

    # ============================================================
    # RUN PHASE
    # ============================================================
    async def run_phase(self):
        """Run phase - protocol checkers already started in start_of_simulation_phase"""
        # 用 UVM objection 控制仿真生命周期
        self.raise_objection()
        self.logger.info("▶️ [RUN] Starting MARB base test run_phase()")

        await self.start_clock()
        await self.trigger_reset()

        # Protocol checkers are running in parallel (started in start_of_simulation_phase)
        # Simulation will continue with test sequences
        await ClockCycles(self.dut.clk, 10)

        self.logger.info("🏁 [RUN] Completed MARB base test run_phase()")
        self.drop_objection()
    async def start_clock(self):
        """启动 DUT 时钟"""
        self.clk_period = randint(2, 5)
        self.logger.info(f"🕒 启动时钟 (period={self.clk_period} ns)")
        cocotb.start_soon(Clock(self.dut.clk, self.clk_period, "ns").start())

    async def trigger_reset(self):
        """产生复位信号"""
        await ClockCycles(self.dut.clk, randint(1, 3))
        self.logger.info("🔁 施加复位信号 ...")
        self.dut.rst.value = 1
        await ClockCycles(self.dut.clk, randint(5, 10))
        self.dut.rst.value = 0
        self.logger.info("✅ Reset 完成")
