""" SDT-UVC sequence library	
- The UVM Sequence is composed of several sequence items which can be put together in different ways to generate various scenarios.
- They are executed by an assigned sequencer which then sends data items to the driver. Hence, sequences make up the core stimuli of any verification plan."""

from pyuvm import uvm_sequence
import vsc
from random import randint
from cocotb.triggers import Timer

from .cl_sdt_seq_item import *
from .sdt_common import *

@vsc.randobj
class cl_sdt_base_seq(uvm_sequence, object):
    """ Base sequence for the SDT agent

    body method should be overwritten in new classes to define sequence."""

    def __init__(self, name = "sdt_base_seq"):
        uvm_sequence.__init__(self, name)
        object.__init__(self)

        # Sequence item
        self.s_item = vsc.rand_attr(cl_sdt_seq_item.create(name + ".sdt_item"))

        # Delay before transaction
        self.delay_before_transaction = vsc.rand_uint32_t()

    @vsc.constraint
    def c_delay_before_transaction(self):
        self.delay_before_transaction in vsc.rangelist(vsc.rng(0, 15))

    async def body(self):
        if self.delay_before_transaction != 0:
            await Timer(self.delay_before_transaction * 1, 'ns')


class cl_sdt_single_seq(cl_sdt_base_seq):
    """Sequence generating one random item"""
    def __init__(self, name = "sdt_single_seq"):
        super().__init__(name)

    async def body(self):
        if self.sequencer.cfg.driver == DriverType.PRODUCER:
            await super().body()

        await self.start_item(self.s_item)

        self.sequencer.logger.debug(self.s_item)

        # Send transaction to driver
        await self.finish_item(self.s_item)

class cl_sdt_single_zd_seq(cl_sdt_single_seq):
    """Sequence generating one random zero delay item"""
    def __init__(self, name = "sdt_single_zd_seq"):
        super().__init__(name)

    @vsc.constraint
    def c_delay_before(self):
        self.delay_before_transaction == 0

    @vsc.constraint
    def c_zero_delay(self):
        self.s_item.no_producer_consumer_delays == 1

class cl_sdt_consumer_rsp_seq(cl_sdt_base_seq):
    """Sequence generating consumer response items"""
    def __init__(self, name = "sdt_consumer_rsp_seq"):
        super().__init__(name)

    async def body(self):
        # Define the body of consumer_rsp_seq from num_consumer_seq
        if self.sequencer.cfg.num_consumer_seq == None:
            while True:
                # Create transaction
                seq_item_name = self.sequencer.get_full_name() + ".consumer_rsp_item"
                self.s_item = cl_sdt_seq_item.create(seq_item_name)

                await self.start_item(self.s_item)

                # Randomize transaction
                self.s_item.randomize()

                self.sequencer.logger.debug(f"Sending item: {self.s_item}")

                # Send transaction to driver
                await self.finish_item(self.s_item)

        elif self.sequencer.cfg.num_consumer_seq == 0:
            pass

        elif self.sequencer.cfg.num_consumer_seq > 0 :
            for _ in range(self.sequencer.cfg.num_consumer_seq):
                # Create transaction
                seq_item_name = self.sequencer.get_full_name() + ".consumer_rsp_item"
                self.s_item = cl_sdt_seq_item.create(seq_item_name)

                await self.start_item(self.s_item)

                # Randomize transaction
                self.s_item.randomize()

                self.sequencer.logger.debug(f"Sending item: {self.s_item}")

                # Send transaction to driver
                await self.finish_item(self.s_item)
        else:
            self.sequencer.logger.critical(f"Num of sequences must be None or >=0, was {self.sequencer.cfg.num_consumer_seq}")


@vsc.randobj
class cl_sdt_count_seq(cl_sdt_base_seq):
    """Sequence generating <count> random item"""
    def __init__(self, name = "sdt_count_seq"):
        super().__init__(name)
        self.count = vsc.rand_uint32_t()

    @vsc.constraint
    def c_count(self):
        self.count in vsc.rangelist(vsc.rng(0, 100))

    async def body(self):
        for _ in range(self.count):
            if self.sequencer.cfg.driver == DriverType.PRODUCER:
                await super().body()

            # Create transaction
            seq_item_name = self.sequencer.get_full_name() + ".sdt_count_seq_item"
            self.s_item = cl_sdt_seq_item.create(seq_item_name)

            await self.start_item(self.s_item)

            # Randomize transaction
            self.s_item.randomize()

            self.sequencer.logger.debug(f"Sending item: {self.s_item}")

            # Send transaction to driver
            await self.finish_item(self.s_item)
            await self.get_response()