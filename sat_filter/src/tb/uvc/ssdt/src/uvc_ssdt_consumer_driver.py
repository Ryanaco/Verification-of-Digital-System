from cocotb.triggers import RisingEdge, ReadOnly
from .uvc_ssdt_base_driver import uvc_ssdt_base_driver

class uvc_ssdt_consumer_driver(uvc_ssdt_base_driver):
    def __init__(self, name, parent):
        super().__init__(name, parent)

    async def driver_loop(self):

        self.logger.debug("Running CONSUMER loop...")
        self.logger.debug(f"CONSUMER (req): data = {self.req}")

        while True:
            await ReadOnly()
            if (self.vif.valid.value.binstr == "1"):
                self.rsp.data = self.vif.data.value
                await RisingEdge(self.cfg.vif.clk)
                break
            await RisingEdge(self.cfg.vif.clk)
        self.logger.debug(f"CONSUMER (rsp): data = {self.rsp}")