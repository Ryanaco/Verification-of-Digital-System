"""SSDT-UVC Monitor

- UVM monitor is responsible for capturing signal activity from the design interface and translate it into transaction level data objects that can be sent to other components.
"""

from cocotb.triggers import RisingEdge, ReadOnly
from pyuvm import uvm_monitor, uvm_analysis_port, ConfigDB
from .uvc_ssdt_seq_item import uvc_ssdt_seq_item


class uvc_ssdt_monitor(uvm_monitor):
    """ SSDT Monitor.
    - Capture pin level signal activity.
    - Translate it to transactions.
    - Broadcasts transactions via analysis port.
    """

    def __init__(self, name="uvc_monitor", parent=None):

        super().__init__(name, parent)

        # Declaration of components
        self.cfg = None                 # Configuration object
        self.mon_analysis_port = None   # Analysis port for transaction item
        self.vif = None                 # Virtual interface object

    def build_phase(self):

        super().build_phase()

        # Get the configuration object
        self.cfg = ConfigDB().get(self, "", "cfg")

        # Create an instance of Virtual interface
        self.vif = self.cfg.vif

        # Create an instance of the Analysis Port
        self.mon_analysis_port = uvm_analysis_port.create(f"{self.get_parent().get_name()}_analysis_port", self)

    async def run_phase(self):

        await super().run_phase()

        # Initialize the sequence item counter
        seq_item_counter = 0

        while True:

            await RisingEdge(self.vif.clk)
            await ReadOnly()        # Assures signals stability. Where there is no further delta steps in the current timestep.

            # Sample whenever 'valid' == 1
            if (self.vif.valid.value.binstr == "1"):

                self.logger.debug("Monitor transaction start ... ")

                # Create an instance of a sequence (transaction) item
                seq_item_name = self.get_full_name() + ".sdt_mon_item_" + str(seq_item_counter)
                item = uvc_ssdt_seq_item.create(seq_item_name)
                seq_item_counter += 1

                item.data = self.vif.data.value.integer

                self.logger.debug(f"Monitor transaction end : {item}")

                # Write to Analysis Port
                self.mon_analysis_port.write(item)