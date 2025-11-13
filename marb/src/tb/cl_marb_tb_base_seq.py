
from pyuvm import *
from cocotb.triggers import Combine
from uvc.sdt.src import *

class cl_marb_tb_base_seq(uvm_sequence):
    """Base sequence for tb for Memory Arbiter"""

    def __init__(self, name = "cl_marb_tb_base_seq"):
        super().__init__(name)

        self.cfg = None

    async def pre_body(self):
        if(self.sequencer is not None):
            self.cfg = self.sequencer.cfg

