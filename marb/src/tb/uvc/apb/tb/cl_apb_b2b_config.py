from pyuvm import uvm_object
from uvc.apb.src.cl_apb_config import cl_apb_config

class cl_apb_b2b_config(uvm_object):
    """Configuration object for the APB testbench"""

    def __init__(self, name = 'cl_apb_b2b_config'):
        super().__init__(name)

        self.apb_producer_cfg = cl_apb_config.create("apb_producer_cfg")
        self.apb_consumer_cfg = cl_apb_config.create("apb_consumer_cfg")