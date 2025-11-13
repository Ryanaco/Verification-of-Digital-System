""" SSDT-UVC B2B virtual sequence library
"""

import cocotb
import vsc
from cocotb.triggers import Combine, ReadOnly, NextTimeStep, First
from pyuvm import uvm_sequence, uvm_root
from uvc.ssdt.src.uvc_ssdt_sequence_lib import uvc_ssdt_default_seq


# ------------------------------------------------------------------------------
# Base sequence class: Declaration of objects mainly.
# ------------------------------------------------------------------------------
class ssdt_b2b_base_seq(uvm_sequence):
    """ Base class for the SSDT B2B sequence.
    - Create a single sequence for the consumer and another for the producer.
    """

    def __init__(self, name="ssdt_b2b_base_seq"):

        super().__init__(name)

        self.cfg = None         # Declaration of configuration object handler
        self.sequencer = None   # Declaration of sequencer

        # Declaration of sequences for each agent
        self.producer_seq = None
        self.consumer_seq = None

    async def pre_body(self):

        if(self.sequencer is not None):
            uvm_root().logger.debug("Getting 'sequencer' from configDB")
            self.cfg = self.sequencer.cfg

    async def body(self):
        """ This must be overwrite/updated by the children class.
        Note that the connection to the sequencer will be done on a 'uvm_test' class.
        """


# ------------------------------------------------------------------------------------------
# Default virtual sequence for the SSDT B2B:
# - Launch a single default SSDT sequence on the producer and consumer.
# ------------------------------------------------------------------------------------------
class ssdt_b2b_default_seq(ssdt_b2b_base_seq):
    """ Default sequence for the SSDT-UVC B2B.
    - Start 2 default SSDT sequences in parallel.
    """

    def __init__(self, name="ssdt_b2b_default_seq"):

        super().__init__(name)

        # Create sequences
        self.producer_seq = uvc_ssdt_default_seq.create("ssdt_b2b_prod_seq")
        self.consumer_seq = uvc_ssdt_default_seq.create("ssdt_b2b_cons_seq")

    async def body(self):

        # Launch sequences
        await super().body()

        prod_task = cocotb.start_soon(self.producer_seq.start(self.sequencer.ssdt_producer_sequencer))
        cons_task = cocotb.start_soon(self.consumer_seq.start(self.sequencer.ssdt_consumer_sequencer))

        # Finishes when the both tasks finishes
        await Combine(prod_task, cons_task)

