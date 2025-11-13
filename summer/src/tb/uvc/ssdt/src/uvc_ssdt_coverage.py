""" SSDT-UVC Coverage collector
"""

import vsc
from pyuvm import uvm_subscriber, ConfigDB
from .uvc_ssdt_seq_item import uvc_ssdt_seq_item


class uvc_ssdt_coverage(uvm_subscriber):

    def __init__(self, name, parent):

        super().__init__(name, parent)
        self.cfg = None

    def build_phase(self):

        self.logger.debug("build_phase() SSDT_Coverage")
        super().build_phase()

        # Create the covergroup

    # "write" method to sample the covergroups


