import logging
from pyuvm import *

class cl_reg_base_seq(uvm_sequence):
    """Base sequence for register sequences"""

    def __init__(self, name="cl_reg_base_seq"):
        super().__init__(name)

        self.start_mask        = 0x00000001
        self.dynamic_prio_mask = 0x00000002

        self.cfg        = None
        self.bus_map    = None
        self.reg_model  = None
        self.logger     = logging.getLogger(name)  # ✅ 安全的 Python logger

    async def pre_body(self):
        if self.sequencer is not None:
            if hasattr(self.sequencer, "reg_model") and self.sequencer.reg_model is not None:
                self.reg_model = self.sequencer.reg_model
                self.bus_map = self.reg_model.bus_map
            else:
                self.reg_model = ConfigDB().get(None, "", "reg_model")
                if self.reg_model is None:
                    raise UVMFatalError("No reg_model found in ConfigDB")
                self.bus_map = self.reg_model.bus_map

            if hasattr(self.sequencer, "cfg") and self.sequencer.cfg is not None:
                self.cfg = self.sequencer.cfg
            else:
                self.cfg = ConfigDB().get(None, "", "cfg")
        else:
            raise UVMFatalError("Sequencer for Reg Model not set")

        if self.bus_map is None:
            raise UVMFatalError("Bus map not set in reg_model")

    async def body(self):
        await super().body()
        self.logger.info("✅ cl_reg_base_seq.body() started with valid bus_map")
