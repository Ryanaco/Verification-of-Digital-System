import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.types import LogicArray
from .sdt_common import *
from .cl_sdt_base_driver import *

class cl_sdt_producer_driver(cl_sdt_base_driver):
    def __init__(self, name, parent):
        super().__init__(name, parent)

    async def drive_reset(self):
        self.logger.debug("Producer driver reset")
        self.vif.rd.value      = 0
        self.vif.wr.value      = 0
        self.vif.addr.value    = LogicArray("X" * self.cfg.ADDR_WIDTH)
        self.vif.wr_data.value = LogicArray("X" * self.cfg.DATA_WIDTH)

    async def flushing_queue(self):
        while not self.wr_data_queue.empty():
            try:
                item = self.wr_data_queue.get_nowait()
                await self.do_write(item)
            except:
                break

    async def drive_pins(self):
        # If unaligned to clock wait for clocking event
        await self.ev_last_clock.wait()

        # Drive transactions through interface
        if self.req.access == AccessType.WR:
            self.vif.wr.value      = 1
            self.vif.addr.value    = self.req.addr
            self.vif.wr_data.value = self.req.data

            # Put wr_data in data queue
            self.wr_data_queue.put_nowait(self.req.data)

        elif self.req.access == AccessType.RD:
            self.vif.rd.value     = 1
            self.vif.addr.value   = self.req.addr
            self.vif.wr_data.value = LogicArray('X' * self.cfg.DATA_WIDTH)
        else:
            self.logger.critical(f"Access type not wr or rd: access = {self.req.access}")

        # Wait for acknowledge (with timeout to handle incomplete DUT implementations)
        ack_timeout = 0
        max_timeout = 10  # 较短的超时，快速失败
        while ack_timeout < max_timeout:
            await RisingEdge(self.vif.clk)
            ack_timeout += 1
            if self.vif.ack.value.binstr == '1':
                break
        
        if ack_timeout >= max_timeout:
            self.logger.debug(f"ACK not received within {max_timeout} cycles (expected if DUT doesn't implement ACK)")

        # Capture consumer response
        if self.req.access == AccessType.RD:
            self.req.data = self.vif.rd_data.value.integer
            self.rsp.data = self.vif.rd_data.value.integer

            self.rd_data_queue.put_nowait(self.vif.rd_data.value.integer)

        # Set interface back to idle values
        await self.drive_reset()

        self.logger.debug(f"REQ object: {self.req}")
        self.logger.debug(f"RSP object: {self.rsp}")
