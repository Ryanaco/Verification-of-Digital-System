from pyuvm import uvm_object, uvm_active_passive_enum
from .ssdt_common import SequenceItemOverride

class uvc_ssdt_config(uvm_object):
    """ Configuration object for SSDT-UVC.
    """
    def __init__(self, name='ssdt_config'):

        super().__init__(name)

        #############################
        # General configuration
        #############################

        # Setting agent type
        # uvm_active_passive_enum.UVM_ACTIVE or uvm_active_passive_enum.UVM_PASSIVE
        self.is_active = uvm_active_passive_enum.UVM_ACTIVE

        # Virtual Interface for SSDT
        self.vif = None

        # Driver type: uvc_ssdt_type_enum.PRODUCER OR uvc_ssdt_type_enum.CONSUMER
        self.driver_type = None

        # Configuration knob for controlling the interface width, default: 1
        self.DATA_WIDTH = 1

        # Control knob for sequence item overriding
        self.seq_item_override = SequenceItemOverride.DEFAULT