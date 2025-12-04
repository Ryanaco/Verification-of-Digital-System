"""
MIF Consumer Sequence
- Runs on the MIF sequencer (Consumer/Memory side)
- Continuously accepts SDT requests and generates dummy responses
- Allows the Memory interface to properly handshake with CIF requests through the arbiters
"""

from pyuvm import *
from uvc.sdt.src import cl_sdt_seq_item, AccessType


class ClMifConsumerSeq(uvm_sequence):
    """
    Basic MIF Consumer Sequence
    - Continuously waits for and responds to SDT items
    - Each item is returned with a default data value
    """

    def __init__(self, name="cl_mif_consumer_seq"):
        super().__init__(name)

    async def body(self):
        # Run for a very long time - let it continuously service requests
        for i in range(1000):  # Arbitrary large number
            # Create a new SDT item for the consumer to handle
            item = cl_sdt_seq_item()
            item.access = AccessType.RD  # Dummy value - will be overwritten by driver
            item.addr = 0  # Dummy value - will be overwritten by driver
            item.data = 0xAA  # Default data for reads (can be randomized)
            
            await self.send_request(item)

    async def send_request(self, item):
        """Send transaction to sequencer"""
        await self.start_item(item)
        await self.finish_item(item)
