from pyuvm import *

class cl_sdt_sequencer(uvm_sequencer):
    """ SDT sequencer: passes sequence items for SDT UVCs """

    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.cfg = None

    def build_phase(self):
        self.logger.info("Start build_phase() -> SDT sequencer")
        super().build_phase()
        self.cfg = ConfigDB().get(self, "", "cfg")
        self.logger.info("End build_phase() -> SDT sequencer")