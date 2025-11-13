from pyuvm import uvm_sequence
from cocotb.triggers import Combine

from uvc.apb.src import *

class cl_apb_b2b_base_seq(uvm_sequence):
    """Base sequence for B2B tb for APB UVC"""
    def __init__(self, name = "cl_apb_b2b_base_seq"):
        super().__init__(name)

        self.cfg = None

    async def pre_body(self):
        if(self.sequencer is not None):
            self.cfg = self.sequencer.cfg


class cl_apb_b2b_single_seq(cl_apb_b2b_base_seq):
    """Start 1 sequence with a RD operation on producer and a sequence with data=2 on cosumer in parallel"""

    def __init__(self, name = "cl_apb_b2b_single_seq"):
        super().__init__(name)

    async def body(self):
        await super().body()

        seq_producer = cl_apb_single_seq("apb_producer")
        with seq_producer.randomize_with() as it:
            it.s_item.op == OpType.RD
        self.sequencer.logger.info(f" producer_seq.s_item: {seq_producer.s_item}")

        seq_consumer = cl_apb_single_seq("apb_consumer")
        with seq_consumer.randomize_with() as it:
            it.s_item.data == 2
        self.sequencer.logger.info(f"consumer_seq.s_item: {seq_consumer.s_item}")

        producer_task = cocotb.start_soon(seq_producer.start(self.sequencer.apb_producer_apb_agent_sequencer))
        consumer_task = cocotb.start_soon(seq_consumer.start(self.sequencer.apb_consumer_apb_agent_sequencer))

        await Combine(producer_task, consumer_task)


class cl_apb_b2b_random_seq(cl_apb_b2b_base_seq):
    """Start sequence 10 times. All sequences should be fully randomized."""
    def __init__(self, name = "cl_apb_b2b_rand_seq"):
        super().__init__(name)

    async def body(self):
        await super().body()

        producer_task = cocotb.start_soon(self.producer_task())
        consumer_task = cocotb.start_soon(self.consumer_task())
        await Combine(producer_task, consumer_task)


    async def producer_task(self):
        seq = cl_apb_single_seq("apb_producer")
        for _ in range(100):
            # Randomizing sequence and sequence item
            seq.randomize()
            await seq.start(self.sequencer.apb_producer_apb_agent_sequencer)

    async def consumer_task(self):
        seq = cl_apb_single_seq("apb_consumer")
        for _ in range(100):
            # Randomizing sequence and sequence item
            seq.randomize()
            await seq.start(self.sequencer.apb_consumer_apb_agent_sequencer)


class cl_apb_b2b_zd_seq(cl_apb_b2b_base_seq):
    """Start sequence 100 times. All sequences should be fully randomized, but no producer consumer delay."""
    def __init__(self, name = "cl_apb_b2b_zd_seq"):
        super().__init__(name)

    async def body(self):
        await super().body()

        producer_task = cocotb.start_soon(self.producer_task())
        consumer_task = cocotb.start_soon(self.consumer_task())
        await Combine(producer_task, consumer_task)


    async def producer_task(self):
        seq = cl_apb_single_zd_seq("apb_producer")
        for _ in range(100):
            # Randomizing sequence and sequence item
            seq.randomize()
            await seq.start(self.sequencer.apb_producer_apb_agent_sequencer)

    async def consumer_task(self):
        seq = cl_apb_single_zd_seq("apb_consumer")
        for _ in range(100):
            # Randomizing sequence and sequence item
            seq.randomize()
            await seq.start(self.sequencer.apb_consumer_apb_agent_sequencer)