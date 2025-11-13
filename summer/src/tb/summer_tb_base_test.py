""" Saturation Filter base UVM Test.
"""

import os, warnings

# CocoTB and VSC
import cocotb
from cocotb.triggers import RisingEdge, ReadOnly
import vsc

# PyUVM
from pyuvm import uvm_test, uvm_report_object, uvm_root, uvm_factory, ConfigDB

# SSDT UVC
from uvc.ssdt.src.uvc_ssdt_interface import ssdt_interface_wrapper
from uvc.ssdt.src.uvc_ssdt_interface_assertions import ssdt_interface_assert_check
from uvc.ssdt.src.ssdt_common import ssdt_seq_item_override, SequenceItemOverride
from uvc.ssdt.src.uvc_ssdt_seq_item import uvc_ssdt_seq_item

@pyuvm.test()
class summer_tb_base_test(uvm_test):
    """ Base test component for the Summer TB.
    """

    def __init__(self, name="summer_base_test", parent=None):
        # ----------------------------------------------------------------------

        super().__init__(name, parent)

        # Configuration object
        # Declare Environment
        # Declare DUT handler

    def build_phase(self):
        super().build_phase()

        # Create configuration object and configure it
        #   - Instantiate interface wrappers
        #   - Access the DUT through the cocotb.top handle
        # Instantiate Environment

    def connect_phase(self):
       super().connect_phase()

       # Connect interfaces

    async def run_phase(self):
        await super().run_phase()

        # Clean inputs
        # Start clock
        # Trigger reset
