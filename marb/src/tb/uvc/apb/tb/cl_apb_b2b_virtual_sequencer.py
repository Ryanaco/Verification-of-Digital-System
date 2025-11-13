""" APB-UVC virtual sequencer"""

from pyuvm import uvm_sequencer, ConfigDB

class cl_apb_b2b_virtual_sequencer(uvm_sequencer):
    """APB testbench virtual sequencer"""

    def __init__(self, name, parent):
        super().__init__(name, parent)

        # Configuration handle
        self.cfg = None

        # Handle to sequencers
        self.apb_producer_apb_agent_sequencer = None
        self.apb_consumer_apb_agent_sequencer = None


    def build_phase(self):
        self.logger.info("Start build_phase() -> APB TB virtual sequencer")
        super().build_phase()

        self.cfg = ConfigDB().get(self, "", "cfg")
        self.logger.info("End build_phase() -> APB TB virtual sequencer")