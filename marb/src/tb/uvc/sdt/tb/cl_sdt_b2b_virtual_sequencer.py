""" SDT-UVC virtual sequencer"""

from pyuvm import uvm_sequencer, ConfigDB

class cl_sdt_b2b_virtual_sequencer(uvm_sequencer):
    """SDT testbench virtual sequencer"""

    def __init__(self, name, parent):
        super().__init__(name, parent)

        # Configuration handle
        self.cfg = None

        # Handle to sequencers
        self.sdt_producer_sdt_agent_sequencer = None
        self.sdt_consumer_sdt_agent_sequencer = None


    def build_phase(self):
        self.logger.info("Start build_phase() -> SDT TB virtual sequencer")
        super().build_phase()

        self.cfg = ConfigDB().get(self, "", "cfg")
        self.logger.info("End build_phase() -> SDT TB virtual sequencer")