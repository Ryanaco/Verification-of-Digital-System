
from pyuvm import uvm_env, ConfigDB
from .cl_apb_b2b_virtual_sequencer import cl_apb_b2b_virtual_sequencer
from uvc.apb.src import *

class cl_apb_b2b_env(uvm_env):
    """UVM environmnet component for the APB testbench"""

    def __init__(self, name, parent):
        super().__init__(name, parent)

        # Configuration
        self.cfg = None

        self.virtual_sequencer = None

        # APB producer and consumer agent
        self.apb_producer = None
        self.apb_consumer = None

    def build_phase(self):
        self.logger.info("Start build_phase() -> APB TB env")
        super().build_phase()
        self.cfg = ConfigDB().get(self, "", "cfg")

        ConfigDB().set(self,"virtual_sequencer", "cfg", self.cfg)
        self.virtual_sequencer = cl_apb_b2b_virtual_sequencer.create("virtual_sequencer", self)

        ConfigDB().set(self,"apb_producer", "cfg", self.cfg.apb_producer_cfg)
        self.apb_producer = cl_apb_agent.create("apb_producer", self)

        ConfigDB().set(self,"apb_consumer", "cfg", self.cfg.apb_consumer_cfg)
        self.apb_consumer = cl_apb_agent.create("apb_consumer", self)

        self.cfg.apb_producer_cfg.is_active = uvm_active_passive_enum.UVM_ACTIVE
        self.cfg.apb_producer_cfg.driver = DriverType.PRODUCER

        self.cfg.apb_consumer_cfg.is_active = uvm_active_passive_enum.UVM_ACTIVE
        self.cfg.apb_consumer_cfg.driver = DriverType.CONSUMER

        self.logger.info("End connect_phase() -> APB TB env")

    def connect_phase(self):
        self.logger.info("Start connect_phase() -> APB TB env")
        super().connect_phase()

        self.virtual_sequencer.apb_producer_apb_agent_sequencer = self.apb_producer.sequencer
        self.virtual_sequencer.apb_consumer_apb_agent_sequencer = self.apb_consumer.sequencer

        self.logger.info("End connect_phase() -> APB TB env")