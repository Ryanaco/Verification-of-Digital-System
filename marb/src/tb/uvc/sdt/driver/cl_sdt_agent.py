""" SDT Agent.
- Provides protocol specific tasks to generate transactions, check the results and perform coverage.
- UVM agent encapsulates the Sequencer, Driver and Monitor into a single entity.
- The components here are instatiated and connected via TLM interfaces.
- Can also have configuration options like:
    - the type of UVM agent (active/passive),
    - knobs to turn on features such as functional coverage, and other similar parameters."""

from pyuvm import *
from .cl_sdt_base_driver import cl_sdt_base_driver
from .cl_sdt_producer_driver import cl_sdt_producer_driver
from .cl_sdt_consumer_driver import cl_sdt_consumer_driver
from .cl_sdt_sequencer import cl_sdt_sequencer
from .cl_sdt_monitor import cl_sdt_monitor
from .cl_sdt_coverage import cl_sdt_coverage
from .sdt_common import *
from .cl_sdt_seq_item import cl_sdt_seq_item


class cl_sdt_agent(uvm_agent):
    """ UVM agent for SDT """

    def __init__(self, name, parent):
        super().__init__(name, parent)

        # Analysis port connected to monitor
        self.ap         = None
        self.request_ap = None

        # Handle to configuration object
        self.cfg = None

        # Transaction sequencer
        self.sequencer = None

        # Signal monitor
        self.monitor = None

        # Signal driver
        self.driver = None

        # Coverage transactor
        self.coverage = None

    def build_phase(self):
        self.logger.info("Start build_phase() -> SDT agent")
        super().build_phase()
        # Construct analysis port
        self.ap = uvm_analysis_port("ap", self)
        self.request_ap = uvm_analysis_port("request_ap", self)

        # Get the configuration object
        self.cfg = ConfigDB().get(self, "", "cfg")

        # Create monitor and pass handle to cfg
        ConfigDB().set(self,"monitor","cfg",self.cfg)
        self.monitor = cl_sdt_monitor.create("monitor", self)

        if self.cfg.is_active == uvm_active_passive_enum.UVM_ACTIVE:
            # Create driver and pass handle to cfg if active
            ConfigDB().set(self, "driver", "cfg", self.cfg)

            if  self.cfg.driver == DriverType.PRODUCER:
                self.driver = cl_sdt_producer_driver.create("driver", self)
            else:
                self.driver = cl_sdt_consumer_driver.create("driver", self)

            # Create sequencer and pass handle to cfg if active
            ConfigDB().set(self, "sequencer", "cfg", self.cfg)
            self.sequencer = cl_sdt_sequencer.create("sequencer", self)

        # Create coverage and pass handle to cfg if active
        ConfigDB().set(self,"coverage", "cfg", self.cfg)
        self.coverage = cl_sdt_coverage.create("coverage", self)

        # Update the sequence item width
        if self.cfg.seq_item_override == SequenceItemOverride.DEFAULT:
            uvm_factory().set_type_override_by_type(cl_sdt_seq_item, sdt_change_width(self.cfg.ADDR_WIDTH, self.cfg.DATA_WIDTH))

        self.logger.info("End build_phase() -> SDT agent")

    def connect_phase(self):
        self.logger.info("Start connect_phase() -> SDT agent")
        super().connect_phase()

        # Connect driver and sequencer
        if self.cfg.is_active == uvm_active_passive_enum.UVM_ACTIVE:
            self.driver.seq_item_port.connect(self.sequencer.seq_item_export)

        # Connect monitor analysis port
        self.monitor.ap.connect(self.ap)
        self.monitor.request_ap.connect(self.request_ap)

        # Connect coverage
        self.monitor.ap.connect(self.coverage.analysis_export)
        self.logger.info("End connect_phase() -> SDT agent")
