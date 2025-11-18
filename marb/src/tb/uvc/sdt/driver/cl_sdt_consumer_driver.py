import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.types import LogicArray
from .cl_sdt_base_driver import *

class cl_sdt_consumer_driver(cl_sdt_base_driver):
    def __init__(self, name, parent):
        super().__init__(name, parent)

    async def drive_reset(self):
        self.logger.debug("Consumer driver reset")
        self.vif.rd_data.value = LogicArray(self.cfg.rd_data_no_ack_value * self.cfg.DATA_WIDTH)
        self.vif.ack.value     = 0

    async def flushing_queue(self):
        self.logger.debug("Consumer flushing queue")
        # Flushing data queue
        while self.rd_data_queue.empty() == False:
            self.rd_data_queue.get_nowait()

    async def drive_pins(self):
        self.logger.debug("Consumer driver waiting for RD or WR")

        # Wait for request phase
        while True:
            await RisingEdge(self.vif.clk)
            if not (self.vif.rd.value != 1 and self.vif.wr.value != 1): break

        self.logger.debug("Received RD/WR request")
        # Capture request from bus
        if self.vif.rd.value == 1:
            self.rsp.access = AccessType.RD
        elif self.vif.wr.value == 1:
            self.rsp.access = AccessType.WR
        self.rsp.addr = self.vif.addr
        self.req.addr = self.vif.addr
        if self.rsp.access == AccessType.WR:
            self.rsp.data = self.cfg.vif.wr_data
            self.req.data = self.cfg.vif.wr_data

        # Delay before response phase
        if self.req.no_producer_consumer_delays != 1 and self.req.consumer_delay_rdwr1_ack1 != 0:
            self.logger.debug(f"debug: Consumer driver delay response {self.req.consumer_delay_rdwr1_ack1} clockcycles")
            await ClockCycles(self.cfg.vif.clk, self.req.consumer_delay_rdwr1_ack1)

        # Acknowledge request and if RD send transaction data
        self.vif.ack.value = 1
        if self.vif.rd == 1:
            self.vif.rd_data.value = self.req.data
            # Put rd_data in queue
            self.rd_data_queue.put_nowait(self.req.data)
        elif self.vif.wr == 1:
            self.wr_data_queue.put_nowait(self.vif.wr_data.value.integer)

        self.logger.debug("Consumer driver have send response")
        await RisingEdge(self.vif.clk)

        # Set values back to idle
        await self.drive_reset()
