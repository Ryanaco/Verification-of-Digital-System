"""SDT-UVC Driver
- The UVM Driver is an active entity that converts abstract transaction to design pin toggles.
- Transaction level objects are obtained from the Sequencer and the UVM Driver drives them to the design via an interface handler."""

from pyuvm import *
import cocotb
from cocotb.triggers import RisingEdge, ClockCycles, Event, Timer
from cocotb.types import LogicArray
from .sdt_common import *

class cl_sdt_base_driver(uvm_driver):
    """Driver for Reset-UVC
    - translates transactions to pin level activity
    - transactions pulled from sequencer by the seq_item_port"""

    def __init__(self, name, parent):
        super().__init__(name, parent)

        # Handle to the configuration object
        self.cfg = None

        # Process
        self.get_and_drive_process = None

        self.ev_last_clock = None

    def build_phase(self):
        self.logger.info("Start build_phase() -> SDT driver")
        super().build_phase()

        # Get the configuration object
        self.cfg = ConfigDB().get(self, "", "cfg")

        self.rd_data_queue = ConfigDB().get(self, '' , 'rd_data_queue')
        self.wr_data_queue = ConfigDB().get(self, '' , 'wr_data_queue')

        # Get the virtual interface from the configuration object
        self.vif = self.cfg.vif

        # Check the virtual interface
        if self.vif == None:
            raise UVMFatalError("SDT driver: No virtual interface set in configuration")

        self.logger.info("End build_phase() -> SDT driver")

    def connect_phase(self):
        self.logger.info("Start connect_phase() -> SDT driver")
        super().connect_phase()

        self.logger.info("End connect_phase() -> SDT driver")

    async def run_phase(self):
        """Run phase:
        * Receives the sequence item.
        * For each sequence item it calls the clock_event, drive_transaction and
        handle_reset tasks in parallel in a fork join_none."""

        self.logger.info("Start run_phase() -> SDT driver")
        await super().run_phase()

        # Starts coroutines in parallel
        cocotb.start_soon(self.clock_event())
        cocotb.start_soon(self.drive_transaction())
        cocotb.start_soon(self.handle_reset())

        self.logger.info("End run_phase() -> SDT driver")

    async def clock_event(self):
        self.ev_last_clock = Event()
        while True:
            await RisingEdge(self.vif.clk)
            self.ev_last_clock.set()

            # Waits until next time step , default unit is step
            await Timer(1)
            self.ev_last_clock.clear()


    async def handle_reset(self):
        """ Kills driver process when reset is active"""
        while True:
            if self.vif.rst.value.binstr == '1':
                if self.get_and_drive_process is not None:
                    self.logger.debug("Process should be killed")
                    self.get_and_drive_process.kill()
                    self.get_and_drive_process = None
                    # Ends any active items
                    try:
                        self.seq_item_port.item_done()
                    except UVMSequenceError:
                        self.logger.info("No current active item")
            await RisingEdge(self.vif.clk)

    async def drive_transaction(self):
        while True:
            await self.drive_reset()
            await self.flushing_queue()

            while self.vif.rst.value.binstr != '0':
                await RisingEdge(self.vif.clk)

            # Passes coroutine to process handle -> possible to .kill() process
            self.get_and_drive_process = cocotb.start_soon(self.get_and_drive_transaction())
            # Waits for process to finish
            await self.get_and_drive_process

    async def get_and_drive_transaction(self):
        # Start driver
        await self.driver_loop()
        self.logger.critical(f"DRIVER, not handled driver {self.get_full_name()}")

    async def drive_reset(self):
        self.logger.info("Base driver - drive_reset task")

    async def flushing_queue(self):
        self.logger.info("Base driver - flushing_queue task")

    async def drive_pins(self):
        self.logger.info("Base driver - drive_pins task")

    async def driver_loop(self):
        while True:
            self.logger.debug("Driver waiting for next seq_item")

            # Waits for sequence item
            self.req = await self.seq_item_port.get_next_item()
            self.logger.debug(f"Driver item: {self.req}")

            # Creates clone of sequence item
            self.rsp = self.req.clone()
            # Set the response ID
            self.rsp.set_context(self.req)
            # Set the transaction ID
            self.rsp.set_id_info(self.req)

            # Drives pins
            self.logger.debug("Driving pins")
            await self.drive_pins()

            # Send response
            self.seq_item_port.item_done()
            self.seq_item_port.put_response(self.rsp)
