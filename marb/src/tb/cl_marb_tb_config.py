from pyuvm import *

from uvc.sdt.src.cl_sdt_config import *
from uvc.apb.src.cl_apb_config import *

class cl_marb_tb_config(uvm_object):
    def __init__(self, name = "cl_marb_tb_config"):
        super().__init__(name)

        self.apb_cfg             = cl_apb_config.create("apb_cfg")
