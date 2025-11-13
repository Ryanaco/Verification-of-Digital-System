from enum import Enum, IntEnum
import vsc
from uvc.ssdt.src.uvc_ssdt_seq_item import uvc_ssdt_seq_item

class uvc_ssdt_type_enum(IntEnum):
    """ Type of driver: PRODUCER or CONSUMER """
    PRODUCER = 0
    CONSUMER = 1

class SequenceItemOverride(Enum):
    """ DEFAULT - agent makes the correct override
        USER_DEFINED - user must call the override mechanism"""
    DEFAULT      = 0
    USER_DEFINED = 1

def ssdt_seq_item_override(data_width = 0):
    """ Method that retuns a class definition which can be used by the UVM Factory to override the base sequence item class.
    The new class definition assures that the agent is using the correct WIDTH (from the configuration object)."""

    @vsc.randobj
    class ssdt_seq_item_updated(uvc_ssdt_seq_item):
        """ Common base sequence item for the sSDT agent"""

        def __init__(self, name = "ssdt_seq_item_updated"):
            super().__init__(name)

        @vsc.constraint
        def ssdt_parameters_update(self):
            """Setting the correct DATA_WIDTH parameter"""
            self.data < 2**data_width

    return ssdt_seq_item_updated