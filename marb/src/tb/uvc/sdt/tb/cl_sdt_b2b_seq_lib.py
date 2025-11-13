from pyuvm import uvm_sequence
from cocotb.triggers import Combine
from uvc.sdt.src import *

class cl_sdt_b2b_base_seq(uvm_sequence):
    """Base sequence for B2B tb for SDT UVC"""
    def __init__(self, name = "cl_sdt_b2b_base_seq"):
        super().__init__(name)

        self.cfg = None

    async def pre_body(self):
        if(self.sequencer is not None):
            self.cfg = self.sequencer.cfg


class cl_sdt_b2b_single_seq(cl_sdt_b2b_base_seq):
    """Start 2 sequences in parallel, one sequence should Read, the other should Write"""

    def __init__(self, name = "cl_sdt_b2b_single_seq"):
        super().__init__(name)

    async def body(self):
        await super().body()

        seq_producer = cl_sdt_single_seq("sdt_producer")
        with seq_producer.randomize_with() as it:
            it.s_item.access == AccessType.RD
            it.s_item.addr == 1
        self.sequencer.logger.info(f" producer_seq.s_item: {seq_producer.s_item}")

        seq_consumer = cl_sdt_single_seq("sdt_consumer")
        with seq_consumer.randomize_with() as it:
            it.s_item.data == 2
        self.sequencer.logger.info(f"consumer_seq.s_item: {seq_consumer.s_item}")

        producer_task = cocotb.start_soon(seq_producer.start(self.sequencer.sdt_producer_sdt_agent_sequencer))
        consumer_task = cocotb.start_soon(seq_consumer.start(self.sequencer.sdt_consumer_sdt_agent_sequencer))

        await Combine(producer_task, consumer_task)


class cl_sdt_b2b_random_seq(cl_sdt_b2b_base_seq):
    """Start sequence 100 times. All sequences should be fully randomized."""
    def __init__(self, name = "cl_sdt_b2b_rand_seq"):
        super().__init__(name)

    async def body(self):
        await super().body()

        producer_task = cocotb.start_soon(self.producer_task())
        consumer_task = cocotb.start_soon(self.consumer_task())
        await Combine(producer_task, consumer_task)


    async def producer_task(self):
        seq = cl_sdt_single_seq("sdt_producer")
        for _ in range(100):
            # Randomizing sequence and sequence item
            seq.randomize()
            await seq.start(self.sequencer.sdt_producer_sdt_agent_sequencer)

    async def consumer_task(self):
        seq = cl_sdt_single_seq("sdt_consumer")
        for _ in range(100):
            # Randomizing sequence and sequence item
            seq.randomize()
            await seq.start(self.sequencer.sdt_consumer_sdt_agent_sequencer)


class cl_sdt_b2b_seq(cl_sdt_b2b_base_seq):
    """Start sequence 100 times. All sequences should be fully randomized, but no producer consumer delay."""
    def __init__(self, name = "cl_sdt_b2b_rand_seq"):
        super().__init__(name)

    async def body(self):
        await super().body()

        producer_task = cocotb.start_soon(self.producer_task())
        consumer_task = cocotb.start_soon(self.consumer_task())
        await Combine(producer_task, consumer_task)


    async def producer_task(self):
        seq = cl_sdt_single_zd_seq("sdt_producer")
        for _ in range(100):
            # Randomizing sequence and sequence item
            seq.randomize()
            await seq.start(self.sequencer.sdt_producer_sdt_agent_sequencer)

    async def consumer_task(self):
        seq = cl_sdt_single_zd_seq("sdt_consumer")
        for _ in range(100):
            # Randomizing sequence and sequence item
            seq.randomize()
            await seq.start(self.sequencer.sdt_consumer_sdt_agent_sequencer)