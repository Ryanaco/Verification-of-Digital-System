""" Saturation Filter Reference Model handler.
"""

import cocotb
from pyuvm import uvm_subscriber, uvm_analysis_port
from ref_model import sat_filter_ref_model_py_wrapper as ref_model
from ref_model.sat_filter_ref_model_utils import SeqItem, SeqItemOut


class sat_filter_ref_model(uvm_subscriber):
    """ Handler for Reference Model."""

    def __init__(self, name="sat_filter_ref_model", parent=None):

        super().__init__(name, parent)

        # Analysis port for sending ref model item
        self.analysis_port = None

        self.threshold = None

    def build_phase(self):
        super().build_phase()

        self.analysis_port = uvm_analysis_port(f"{self.get_name()}_analysis_port", self)

    def write(self, item):
        # The 'ref_model_input' structure is used to pass the threshold value.
        seq_input_item = SeqItem(THRESHOLD = self.threshold)
        seq_output_item = SeqItemOut()

        self.logger.debug(f"-------------------------------")
        self.logger.info(f"Get item : {item}")

        output_item = item.clone()

        # Update values
        seq_input_item.set_values(item.data)

        # Send input item to reference model
        ref_model.sat_filter_operation(seq_input_item, seq_output_item)

        output_item.data = seq_output_item.data
        output_item.valid = seq_output_item.valid

        self.logger.debug(f"Output_item : {output_item}")
        self.analysis_port.write(output_item)