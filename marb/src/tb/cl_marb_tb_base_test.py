import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
import os, warnings
from random import randint
import vsc
import pyuvm

from pyuvm import *
from uvc.apb.src import *
from uvc.sdt.src import *
from uvc.sdt.src.cl_sdt_config import cl_sdt_config
from cl_marb_tb_config import cl_marb_tb_config
from cl_marb_tb_env import cl_marb_tb_env

_LOG_LEVELS = ["DEBUG", "CRITICAL", "ERROR", "WARNING", "INFO", "NOTSET", "NullHandler"]

@pyuvm.test()
class cl_marb_tb_base_test(uvm_test):
    def __init__(self, name="cl_marb_tb_base_test", parent=None):
        # Handle log level
        if os.getenv("PYUVM_LOG_LEVEL") in _LOG_LEVELS:
            _PYUVM_LOG_LEVEL = os.getenv('PYUVM_LOG_LEVEL')
        else:
            _PYUVM_LOG_LEVEL = "INFO"

        uvm_report_object.set_default_logging_level(_PYUVM_LOG_LEVEL)
        super().__init__(name, parent)

        self.dut = cocotb.top
        self.apb_if = None
        self.cfg = None
        self.marb_tb_env = None
        warnings.simplefilter("ignore")

    def build_phase(self):
        self.logger.info("Start build_phase() -> MARB base test")
        super().build_phase()

        # --- 创建配置对象 ---
        self.cfg = cl_marb_tb_config("cfg")

        # --- APB CONFIG ---
        self.cfg.apb_cfg.driver = apb_common.DriverType.PRODUCER
        self.cfg.apb_cfg.seq_item_override = apb_common.SequenceItemOverride.USER_DEFINED
        self.cfg.apb_cfg.ADDR_WIDTH = 32
        self.cfg.apb_cfg.DATA_WIDTH = 32
        self.cfg.apb_cfg.STRB_WIDTH = 4
        self.cfg.apb_cfg.enable_masked_data = False
        self.cfg.apb_cfg.active_low_reset = False

        # --- 创建 APB 接口 ---
        self.apb_if = cl_apb_interface(self.dut.clk, self.dut.rst)
        self.cfg.apb_cfg.vif = self.apb_if
        self.apb_if._set_width_parameters(
            self.cfg.apb_cfg.ADDR_WIDTH,
            self.cfg.apb_cfg.DATA_WIDTH
        )

        # --- SDT CONFIG (3 CIF + 1 MIF) ---
        self.cfg.sdt_cif_cfgs = []
        for i in range(3):
            cif_cfg = cl_sdt_config()
            cif_cfg.driver = sdt_common.DriverType.PRODUCER
            cif_cfg.vif = cl_sdt_interface(self.dut.clk, self.dut.rst, name=f"cif{i}")
            self.cfg.sdt_cif_cfgs.append(cif_cfg)

        self.cfg.sdt_mif_cfg = cl_sdt_config()
        self.cfg.sdt_mif_cfg.driver = sdt_common.DriverType.CONSUMER
        self.cfg.sdt_mif_cfg.vif = cl_sdt_interface(self.dut.clk, self.dut.rst, name="mif")

        # --- 创建环境并配置 ---
        ConfigDB().set(self, "marb_tb_env", "cfg", self.cfg)
        self.marb_tb_env = cl_marb_tb_env("marb_tb_env", self)

        # （可选）此处可添加寄存器模型绑定逻辑
        # self.marb_tb_env.reg_model.set_base_addr(0x0000)

        self.logger.info("End build_phase() -> MARB base test")

    def connect_phase(self):
        self.logger.info("Start connect_phase() -> MARB base test")
        super().connect_phase()

        # --- 连接寄存器模型与 APB sequencer ---
        if hasattr(self.marb_tb_env, "reg_model") and self.marb_tb_env.reg_model is not None:
            self.marb_tb_env.reg_model.bus_map.set_sequencer(self.marb_tb_env.apb_agent.sequencer)
        else:
            self.logger.warning("⚠️ reg_model 未定义，跳过 bus_map 连接。")

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
            slverr_signal=self.dut.conf_slverr
        )

        self.logger.info("End connect_phase() -> MARB base test")

    async def run_phase(self):
        self.logger.info("Start run_phase() -> MARB base test")
        await super().run_phase()

        await self.start_clock()
        await self.trigger_reset()

        self.logger.info("End run_phase() -> MARB base test")

    async def start_clock(self):
        """启动 DUT 时钟"""
        self.clk_period = randint(2, 5)
        self.logger.info(f"Starting clock with period = {self.clk_period} ns")
        cocotb.start_soon(Clock(self.dut.clk, self.clk_period, 'ns').start())

    async def trigger_reset(self):
        """产生复位信号"""
        await ClockCycles(self.dut.clk, randint(1, 3))
        self.logger.info("Applying reset...")
        self.dut.rst.value = 1
        await ClockCycles(self.dut.clk, randint(5, 10))
        self.dut.rst.value = 0
        self.logger.info("Reset Done")
