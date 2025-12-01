import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.types import LogicArray
from .cl_sdt_base_driver import *

class cl_sdt_consumer_driver(cl_sdt_base_driver):
    """MIF Consumer driver - responds to producer requests independently"""
    
    def __init__(self, name, parent):
        super().__init__(name, parent)

    async def drive_reset(self):
        """Reset ACK and RD_DATA to idle state"""
        self.logger.debug("Consumer driver reset")
        self.vif.rd_data.value = LogicArray(self.cfg.rd_data_no_ack_value * self.cfg.DATA_WIDTH)
        self.vif.ack.value     = 0

    async def flushing_queue(self):
        """Flush any remaining data from queues"""
        while not self.rd_data_queue.empty():
            try:
                item = self.rd_data_queue.get_nowait()
            except:
                break

    # ✅ Override driver_loop for consumer: listen independently
    async def driver_loop(self):
        """Consumer driver continuously listens for and responds to requests.
        
        Unlike producer driver, consumer doesn't wait for sequence items.
        Instead, it monitors rd/wr request signals and responds with ACK.
        """
        self.logger.info("🎧 Consumer driver_loop started - listening for requests")
        
        while True:
            # Wait for and respond to next request
            await self.drive_pins()
            # Loop continues immediately to listen for next request

    async def drive_pins(self):
        """Wait for RD/WR request and assert ACK response"""
        self.logger.debug("Consumer waiting for RD or WR request")

        # Wait for request phase - RD or WR must be active
        while True:
            await RisingEdge(self.vif.clk)
            rd_active = int(self.vif.rd.value) == 1
            wr_active = int(self.vif.wr.value) == 1
            if rd_active or wr_active:
                break

        self.logger.debug("✅ Received RD/WR request")
        
        # Now that request is active, safely read address and data
        # (they should be valid when rd or wr is asserted)
        rd_active = int(self.vif.rd.value) == 1
        wr_active = int(self.vif.wr.value) == 1
        
        try:
            req_addr = int(self.vif.addr.value)
        except ValueError:
            req_addr = 0
            self.logger.warning("Could not parse addr, defaulting to 0")
            
        req_data = 0
        if wr_active:
            try:
                req_data = int(self.vif.wr_data.value)
            except ValueError:
                req_data = 0
                self.logger.warning("Could not parse wr_data, defaulting to 0")
            self.logger.debug(f"Consumer RX: WR@{hex(req_addr)}={hex(req_data)}")
        else:
            self.logger.debug(f"Consumer RX: RD@{hex(req_addr)}")

        # Delay before response (usually 0 - respond same or next cycle)
        delay_cycles = 0
        if delay_cycles > 0:
            await ClockCycles(self.vif.clk, delay_cycles)

        # ✅ Assert ACK
        self.logger.debug("🔔 Asserting ACK")
        self.vif.ack.value = 1
        
        if rd_active:
            # Return distinctive test data for reads
            dummy_data = 0xAB
            self.vif.rd_data.value = dummy_data
            self.logger.debug(f"Consumer TX: RD_DATA={hex(dummy_data)}")

        self.logger.debug("Consumer ACK hold - 1 cycle")
        await RisingEdge(self.vif.clk)

        # Deassert ACK
        self.logger.debug("Deasserting ACK")
        await self.drive_reset()
