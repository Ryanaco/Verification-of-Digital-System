from pyuvm import uvm_object
from uvc.sdt.src.cl_sdt_config import cl_sdt_config

class cl_sdt_b2b_config(uvm_object):
    """Configuration object for the SDT testbench"""

    def __init__(self, name = 'cl_sdt_b2b_config'):
        super().__init__(name)

        self.sdt_producer_cfg = cl_sdt_config.create("sdt_producer_cfg")
        self.sdt_consumer_cfg = cl_sdt_config.create("sdt_consumer_cfg")