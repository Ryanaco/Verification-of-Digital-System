"""SDT-UVC Monitor
- UVM monitor is responsible for capturing signal activity from the design interface and translates it into transaction level data objects that can be sent to other components."""

from pyuvm import *
import cocotb
from cocotb.triggers import RisingEdge, ReadOnly

from .cl_sdt_seq_item import *
from .sdt_common import *

class cl_sdt_monitor(uvm_monitor):
    """SDT Monitor

    - Capture pin level signal activity
    - Translate it to transactions
    - Broadcasts transactions via analysis port"""

    def __init__(self, name, parent):
        super().__init__(name, parent)

        # Analysis port for broadcasting of collected transactions
        self.ap = None
        self.request_ap = None

        # Handle to the configuration object
        self.cfg = None

        # Handle to the virtual interface
        self.vif = None

        # Monitor process
        self.monitor_loop_process = None

        # Clock cycle counter
        self.clk_cyc_cnt = 0

    def build_phase(self):
        self.logger.info("Start build_phase() -> SDT monitor")
        super().build_phase()

        # Get the configuration object
        self.cfg = ConfigDB().get(self, "", "cfg")

	    # Construct the analysis port
        self.ap = uvm_analysis_port("ap",self)
        self.request_ap = uvm_analysis_port("request_ap", self)

        # Get the virtual interface from the configuration object
        self.vif = self.cfg.vif

        # Check the virtual interface
        if self.vif == None:
            raise UVMFatalError("SDT monitor: No virtual interface set in configuration")

        self.logger.info("End build_phase() -> SDT monitor")

    def connect_phase(self):
        self.logger.info("Start connect_phase() -> SDT monitor")
        super().connect_phase()

        self.logger.info("End connect_phase() -> SDT monitor")

    async def run_phase(self):
        self.logger.info("Start run_phase() -> SDT monitor")
        await super().run_phase()

        # Start all coroutines in parallel
        cocotb.start_soon(self.clock_count())
        cocotb.start_soon(self.handle_reset())
        cocotb.start_soon(self.monitor_transaction())

        self.logger.info("End run_phase() -> SDT monitor")

    async def clock_count(self):
        while True:
            await RisingEdge(self.cfg.vif.clk)
            self.clk_cyc_cnt += 1

    async def handle_reset(self):
        """Kills monitor process when reset is active"""

        while True:
            if self.cfg.vif.rst.value.binstr == '1':
                if self.monitor_loop_process != None:
                    self.monitor_loop_process.kill()
            await RisingEdge(self.cfg.vif.clk)

    async def monitor_transaction(self):
        while True:
            while self.cfg.vif.rst.value.binstr != '0':
                await RisingEdge(self.cfg.vif.clk)
            self.monitor_loop_process = cocotb.start_soon(self.monitor_loop())
            await self.monitor_loop_process

    async def monitor_loop(self):
        """Monitor loop and pin wiggling"""

        while True:
            # Transaction item
            seq_item_name = self.get_full_name() + "sdt_mon_item"
            item = cl_sdt_seq_item.create(seq_item_name)

            # Monitor process
            self.logger.debug(f"Monitor transaction start #{self.clk_cyc_cnt}: {item}")
            await self.monitor_observe_pins(item)
            self.logger.debug(f"Monitor transaction end #{self.clk_cyc_cnt}: {item}")

            # Write on analysis port
            self.ap.write(item)

    async def monitor_observe_pins(self,item):
        # For capturing clock cycle count
        cc_now = 0

        while True:
            await ReadOnly()
            if not (self.cfg.vif.rd.value.binstr != '1' and self.cfg.vif.wr.value.binstr != '1'):
                break
            await RisingEdge(self.cfg.vif.clk)

        # Capture request phase
        if self.cfg.vif.rd.value == 1:
            item.access = AccessType.RD
        elif self.cfg.vif.wr.value == 1:
            item.access = AccessType.WR
            item.data = self.cfg.vif.wr_data.value.integer

        if self.cfg.vif.addr.value.binstr != 'x' * self.cfg.ADDR_WIDTH:
            item.addr = self.cfg.vif.addr.value.integer
        else:
            self.logger.warning(f"addr has value: {self.cfg.vif.addr.value.binstr}")

        # Send client request
        if self.cfg.driver == DriverType.PRODUCER:
            self.request_ap.write(item)

        # Wait for response phase
        cc_now = self.clk_cyc_cnt

        while True:
            await RisingEdge(self.cfg.vif.clk)
            if self.cfg.vif.ack.value.binstr == '1':
                break

        item.consumer_delay_rdwr1_ack1 = self.clk_cyc_cnt - cc_now

        # Capture response
        if item.access == AccessType.RD:
            item.data = self.cfg.vif.rd_data.value.integer