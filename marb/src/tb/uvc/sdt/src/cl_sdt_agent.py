""" SDT Agent. """

from pyuvm import *
from .cl_sdt_sequencer import cl_sdt_sequencer
from .cl_sdt_monitor import cl_sdt_monitor
from .cl_sdt_coverage import cl_sdt_coverage
from .sdt_common import *
from .cl_sdt_seq_item import cl_sdt_seq_item


class cl_sdt_agent(uvm_agent):
    """ UVM agent for SDT """

    def __init__(self, name, parent):
        super().__init__(name, parent)

        self.ap         = None
        self.request_ap = None
        self.cfg        = None
        self.sequencer  = None
        self.monitor    = None
        self.driver     = None
        self.coverage   = None

    def build_phase(self):
        self.logger.info("Start build_phase() -> SDT agent")
        super().build_phase()

        # Construct analysis ports
        self.ap = uvm_analysis_port("ap", self)
        self.request_ap = uvm_analysis_port("request_ap", self)

        # Get configuration
        self.cfg = ConfigDB().get(self, "", "cfg")

        # Create monitor (always present)
        ConfigDB().set(self, "monitor", "cfg", self.cfg)
        self.monitor = cl_sdt_monitor.create("monitor", self)

        if self.cfg.is_active == uvm_active_passive_enum.UVM_ACTIVE:
            # Create sequencer
            ConfigDB().set(self, "sequencer", "cfg", self.cfg)
            self.sequencer = cl_sdt_sequencer.create("sequencer", self)

            # 如果你有 driver 类，可以在这里创建：
            # ConfigDB().set(self, "driver", "cfg", self.cfg)
            # self.driver = cl_sdt_driver.create("driver", self)

        # Create coverage
        ConfigDB().set(self, "coverage", "cfg", self.cfg)
        self.coverage = cl_sdt_coverage.create("coverage", self)

        # Update sequence item width
        if self.cfg.seq_item_override == SequenceItemOverride.DEFAULT:
            uvm_factory().set_type_override_by_type(
                cl_sdt_seq_item,
                sdt_change_width(self.cfg.ADDR_WIDTH, self.cfg.DATA_WIDTH)
            )

        self.logger.info("End build_phase() -> SDT agent")

    def connect_phase(self):
        self.logger.info("Start connect_phase() -> SDT agent")
        super().connect_phase()

        # 🩵 设置虚拟接口（关键修复点）
        # 从 ConfigDB 中取出 vif（在 tb 顶层 environment 设置的）
        self.cfg.vif = ConfigDB().get(self, "", "vif")
        self.monitor.cfg = self.cfg
        self.monitor.vif = self.cfg.vif
        self.monitor.cfg.vif = self.cfg.vif

        # 如果有 driver，也要给 driver 配置 vif
        if self.cfg.is_active == uvm_active_passive_enum.UVM_ACTIVE and hasattr(self, "driver") and self.driver is not None:
            self.driver.vif = self.cfg.vif
            self.driver.cfg.vif = self.cfg.vif

        # Connect analysis ports
        self.monitor.ap.connect(self.ap)
        self.monitor.request_ap.connect(self.request_ap)
        self.monitor.ap.connect(self.coverage.analysis_export)

        self.logger.info("End connect_phase() -> SDT agent")
