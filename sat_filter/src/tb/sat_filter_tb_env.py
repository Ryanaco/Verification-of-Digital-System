""" Saturation Filter Environment UVM component.

- A UVM environment contains several, reusable verification components, such as, agents, scoreboard, coverage collector, ...
- Here is defined their default configuration required by the test case.
"""

from pyuvm import uvm_env, uvm_active_passive_enum, ConfigDB

from sat_filter_tb_virt_sequencer import sat_filter_tb_virt_sequencer
from sat_filter_scb import sat_filter_scoreboard
from sat_filter_ref_model import sat_filter_ref_model

from uvc.ssdt.src.ssdt_common import uvc_ssdt_type_enum, SequenceItemOverride
from uvc.ssdt.src.uvc_ssdt_agent import uvc_ssdt_agent


class sat_filter_tb_env(uvm_env):
    """ UVM Environment component for the Saturation Filter TB.
    """

    def __init__(self, name, parent):

        super().__init__(name, parent)

        # Declare configuration object
        self.cfg = None

        # Declare Virtual Sequencer
        self.virtual_sequencer = None

        # Declare Scoreboard

        # Declare Ref. model handler
        self.ref_model_handler = None

        # Declare Agents
        self.uvc_ssdt_producer = None
        self.uvc_ssdt_consumer = None


    def build_phase(self):
        self.logger.debug("build_phase Environment")
        super().build_phase()

        # Get the configuration object
        self.cfg = ConfigDB().get(self, "", "cfg")
        self.logger.debug(f"config  {self.cfg}")

        # Instantiate Virtual Sequencer
        self.logger.debug("Creating Virtual Sequencer...")
        ConfigDB().set(self, "sat_filter_tb_top_seqr", "cfg", self.cfg)
        self.virtual_sequencer = sat_filter_tb_virt_sequencer.create("sat_filter_tb_top_seqr", self)
        self.logger.debug(f"Virtual Sequencer < {self.virtual_sequencer} > created")

        # Instantiate Scoreboard

        # Instantiate Reference Model
        self.logger.debug(f"Creating Reference Model...")
        self.ref_model_handler = sat_filter_ref_model.create("sat_filter_ref_model", self)
        self.ref_model_handler.threshold = self.cfg.threshold
        self.logger.debug(f"Reference Model < {self.ref_model_handler} > created")

        # Instantiate Agents
        self.logger.debug("Creating Agents...")

        # ----- Producer ------
        self.uvc_ssdt_producer = uvc_ssdt_agent.create("uvc_ssdt_producer", self)

        ConfigDB().set(self,"uvc_ssdt_producer", "cfg", self.cfg.ssdt_prod_cfg)
        self.cfg.ssdt_prod_cfg.is_active         = uvm_active_passive_enum.UVM_ACTIVE
        self.cfg.ssdt_prod_cfg.driver_type       = uvc_ssdt_type_enum.PRODUCER
        self.cfg.ssdt_prod_cfg.seq_item_override = SequenceItemOverride.USER_DEFINED

        self.logger.debug(f"\nAgent < {self.uvc_ssdt_producer} > created with the following configs {self.uvc_ssdt_producer.cfg}\n")

        # ----- Consumer ------
        self.uvc_ssdt_consumer = uvc_ssdt_agent.create("uvc_ssdt_consumer", self)

        ConfigDB().set(self,"uvc_ssdt_consumer", "cfg", self.cfg.ssdt_cons_cfg)
        self.cfg.ssdt_cons_cfg.is_active         = uvm_active_passive_enum.UVM_ACTIVE
        self.cfg.ssdt_cons_cfg.driver_type       = uvc_ssdt_type_enum.CONSUMER
        self.cfg.ssdt_cons_cfg.seq_item_override = SequenceItemOverride.USER_DEFINED

        self.logger.debug(f"\nAgent < {self.uvc_ssdt_consumer} > created with the following configs {self.uvc_ssdt_consumer.cfg}\n")

        # -----------------


    def connect_phase(self):

        self.logger.debug(f"connect_phase() Environment")
        super().connect_phase()

        # Connect agents' sequencer to virtual sequencer
        self.logger.debug(f"Connecting virtual sequencer: {self.virtual_sequencer}")

        self.virtual_sequencer.ssdt_producer_sequencer = self.uvc_ssdt_producer.sequencer
        self.virtual_sequencer.ssdt_consumer_sequencer = self.uvc_ssdt_consumer.sequencer

        self.logger.debug(f"Virtual sequencer connected: {self.virtual_sequencer}")

        # Connect consumer agents analysis port with scoreboard

        # Connect producer agent analysis port with ref. model handler
        self.uvc_ssdt_producer.analysis_port.connect(self.ref_model_handler.analysis_export)

        # Connect ref model handler analysis port to the scoreboard

