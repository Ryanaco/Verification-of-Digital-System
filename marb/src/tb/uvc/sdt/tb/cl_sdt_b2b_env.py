
from pyuvm import uvm_env, ConfigDB
from cl_sdt_b2b_virtual_sequencer import cl_sdt_b2b_virtual_sequencer
from uvc.sdt.src import *

class cl_sdt_b2b_env(uvm_env):
    """UVM environmnet component for the SDT testbench"""

    def __init__(self, name, parent):
        super().__init__(name, parent)

        # Configuration
        self.cfg = None

        self.virtual_sequencer = None

        # SDT producer and consumer agent
        self.sdt_producer = None
        self.sdt_consumer = None

    def build_phase(self):
        self.logger.info("Start build_phase() -> SDT TB env")
        super().build_phase()
        self.cfg = ConfigDB().get(self, "", "cfg")

        ConfigDB().set(self,"virtual_sequencer", "cfg", self.cfg)
        self.virtual_sequencer = cl_sdt_b2b_virtual_sequencer.create("virtual_sequencer", self)

        ConfigDB().set(self,"sdt_producer", "cfg", self.cfg.sdt_producer_cfg)
        self.sdt_producer = cl_sdt_agent.create("sdt_producer", self)

        ConfigDB().set(self,"sdt_consumer", "cfg", self.cfg.sdt_consumer_cfg)
        self.sdt_consumer = cl_sdt_agent.create("sdt_consumer", self)

        self.cfg.sdt_producer_cfg.is_active = uvm_active_passive_enum.UVM_ACTIVE
        self.cfg.sdt_producer_cfg.driver = DriverType.PRODUCER

        self.cfg.sdt_consumer_cfg.is_active = uvm_active_passive_enum.UVM_ACTIVE
        self.cfg.sdt_consumer_cfg.driver = DriverType.CONSUMER

        self.logger.info("End connect_phase() -> SDT TB env")

    def connect_phase(self):
        self.logger.info("Start connect_phase() -> SDT TB env")
        super().connect_phase()

        self.virtual_sequencer.sdt_producer_sdt_agent_sequencer = self.sdt_producer.sequencer
        self.virtual_sequencer.sdt_consumer_sdt_agent_sequencer = self.sdt_consumer.sequencer

        self.logger.info("End connect_phase() -> SDT TB env")