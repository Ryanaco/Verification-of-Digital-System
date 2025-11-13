from cocotb.triggers import RisingEdge
from .uvc_ssdt_base_driver import uvc_ssdt_base_driver

class uvc_ssdt_producer_driver(uvc_ssdt_base_driver):
    def __init__(self, name, parent):
        super().__init__(name, parent)

    async def driver_loop(self):

        self.logger.debug("Running PRODUCER loop...")
        self.logger.debug(f"PRODUCER (req): data = {self.req.data}")

        self.vif.data.value  = self.req.data
        self.vif.valid.value = 1
        self.rsp.data        = self.req.data

        await RisingEdge(self.vif.clk)

        self.reset_bus()
        self.logger.debug(f"PRODUCER (rsp): data = {self.rsp.data}")

    def reset_bus(self):
        self.vif.data.value  = 0
        self.vif.valid.value = 0