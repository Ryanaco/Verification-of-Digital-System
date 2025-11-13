
from pyuvm import *

class cl_marb_tb_virtual_sequencer(uvm_sequencer):

    def __init__(self, name, parent):
        super().__init__(name, parent)

        # Configuration object handler
        self.cfg = None

        # Register model handler
        self.reg_model = None


    def build_phase(self):
        self.logger.info("Start build_phase() -> MARB virtual sequencer")
        super().build_phase()

        # Get the configuration object
        self.cfg = ConfigDB().get(self, "", "cfg")

        self.logger.info("End build_phase() -> MARB virtual sequencer")