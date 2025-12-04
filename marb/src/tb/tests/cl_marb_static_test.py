import os
import warnings
from random import randint

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer
import logging
import vsc
import pyuvm
from pyuvm import *

# -------------------------------------------------------
# Import UVC components
# -------------------------------------------------------
from uvc.apb.src import *          # apb_common, cl_apb_interface, cl_apb_seq_item, ...
from uvc.apb.src.apb_common import OpType
from uvc.sdt.src import *          # sdt_common, cl_sdt_interface, cl_sdt_seq_item, ...
from uvc.sdt.src.cl_sdt_config import cl_sdt_config

from cl_marb_tb_config import cl_marb_tb_config
from cl_marb_tb_env import cl_marb_tb_env
from cl_marb_tb_base_test import cl_marb_tb_base_test

seq_logger = logging.getLogger("MARB_STATIC_SEQ")
_LOG_LEVELS = ["DEBUG", "CRITICAL", "ERROR", "WARNING", "INFO", "NOTSET", "NullHandler"]


# ============================================================
# APB register addresses / field definitions (based on spec)
# ============================================================

# Control register address: enable + mode
ARB_CTRL_ADDR = 0x00

# Dynamic priority register address (32-bit, 8-bit × 4 CIF slots)
DPRIO_ADDR = 0x04

# Mode definition: 0 = static, 1 = dynamic
ARB_MODE_STATIC = 0x0

# Default static priority: CIF0 > CIF1 > CIF2
# Higher number = higher priority (per DPrio definition)
C0_PRIORITY = 2
C1_PRIORITY = 1
C2_PRIORITY = 0


# ============================================================
# APB configuration sequence: set arbitration mode + client priorities
# ============================================================
class cl_marb_static_apb_cfg_seq(uvm_sequence):

    def __init__(self, name="cl_marb_static_apb_cfg_seq"):
        super().__init__(name)

    async def body(self):
        seq_logger.info("[APB_CFG] Configure arbiter as STATIC mode + priorities")

        # ------------------------------------------------------
        # 1) Write control register: enable=1, mode=STATIC (0)
        #    control[0] = enable
        #    control[2:1] = mode
        # ------------------------------------------------------
        ctrl_value = (ARB_MODE_STATIC << 1) | 0x1

        item = cl_apb_seq_item.create("arb_ctrl_item")
        item.addr = ARB_CTRL_ADDR
        item.data = ctrl_value
        item.op   = OpType.WR
        item.strb = 0xF
        await self.start_item(item)
        await self.finish_item(item)

        seq_logger.info(
            f"  - Set CTRL @0x{ARB_CTRL_ADDR:08X} = 0x{ctrl_value:08X} "
            f"(mode=STATIC, enable=1)"
        )

        # ------------------------------------------------------
        # 2) Write DPrio register (optional for STATIC mode,
        #    only for visibility)
        #    DPrio[ 7: 0] = CIF0
        #          [15: 8] = CIF1
        #          [23:16] = CIF2
        # ------------------------------------------------------
        dprio_value = (
            (C2_PRIORITY & 0xFF) << 16 |
            (C1_PRIORITY & 0xFF) << 8  |
            (C0_PRIORITY & 0xFF)
        )

        item = cl_apb_seq_item.create("dprio_item")
        item.addr = DPRIO_ADDR
        item.data = dprio_value
        item.op   = OpType.WR
        item.strb = 0xF
        await self.start_item(item)
        await self.finish_item(item)

        seq_logger.info(
            f"  - Set DPRIO @0x{DPRIO_ADDR:08X} = 0x{dprio_value:08X} "
            f"(c0={C0_PRIORITY}, c1={C1_PRIORITY}, c2={C2_PRIORITY})"
        )

        seq_logger.info("[APB_CFG] Arbiter static config done")


# ============================================================
# SDT client sequence (Producer): random traffic + overlapping addresses
# ============================================================
class cl_marb_static_cif_seq(uvm_sequence):
    """
    Random traffic generator for a single CIF:
      - Random read/write inside a small address window
      - Random number of transactions
      - Back-to-back operations to create contention between CIFs
    """

    def __init__(self,
                 name="cl_marb_static_cif_seq",
                 client_id=0,
                 base_addr=0x10,
                 num_min=5,
                 num_max=15):
        super().__init__(name)
        self.client_id = client_id
        self.base_addr = base_addr
        self.num_min   = num_min
        self.num_max   = num_max

    async def body(self):
        num_txn = randint(self.num_min, self.num_max)
        seq_logger.info(
            f"[CIF{self.client_id}] Static traffic start, num_txn={num_txn}, "
            f"base_addr=0x{self.base_addr:02X}"
        )

        for i in range(num_txn):

            # Random address within base_addr .. base_addr+0x0F
            addr = self.base_addr + randint(0, 0x0F)

            # 0: READ, 1: WRITE
            access = randint(0, 1)
            data   = randint(0, 0xFF)

            item = cl_sdt_seq_item.create(f"cif{self.client_id}_item{i}")
            item.addr   = addr
            item.data   = data
            item.access = access

            await self.start_item(item)
            await self.finish_item(item)

            if access == 1:
                seq_logger.info(
                    f"  - CIF{self.client_id} WRITE addr=0x{addr:02X}, data=0x{data:02X}"
                )
            else:
                seq_logger.info(
                    f"  - CIF{self.client_id} READ  addr=0x{addr:02X}"
                )

            # Add small random idle time to create address overlap timing
            await Timer(randint(0, 10), units="ns")

        seq_logger.info(f"[CIF{self.client_id}] Static traffic sequence done")


# ============================================================
# Virtual Sequence: control APB + launch CIF traffic
# ============================================================
class cl_marb_static_vseq(uvm_sequence):
    """
    Virtual sequence for STATIC mode concurrent random traffic.
    """

    def __init__(self, name="cl_marb_static_vseq"):
        super().__init__(name)

    async def body(self):
        vseqr = self.sequencer
        seq_logger.info("[VSEQ] Static random traffic virtual sequence start")

        # 1) Configure static mode via APB
        apb_cfg_seq = cl_marb_static_apb_cfg_seq("apb_cfg_seq")
        await apb_cfg_seq.start(vseqr.apb_seqr)
        seq_logger.info("[VSEQ] APB static config completed")

        # 2) Select random overlapping address window
        base_addr = randint(0x10, 0x40)
        seq_logger.info(
            f"[VSEQ] Conflict address window base = 0x{base_addr:02X}"
        )

        cif0_seq = cl_marb_static_cif_seq("c0_seq", client_id=0, base_addr=base_addr)
        cif1_seq = cl_marb_static_cif_seq("c1_seq", client_id=1, base_addr=base_addr)
        cif2_seq = cl_marb_static_cif_seq("c2_seq", client_id=2, base_addr=base_addr)

        seq_logger.info("[VSEQ] Launch CIF0/1/2 sequences in parallel ...")

        # Parallel execution
        t0 = cocotb.start_soon(cif0_seq.start(vseqr.cif_seqrs[0]))
        t1 = cocotb.start_soon(cif1_seq.start(vseqr.cif_seqrs[1]))
        t2 = cocotb.start_soon(cif2_seq.start(vseqr.cif_seqrs[2]))

        await t0
        await t1
        await t2

        seq_logger.info("[VSEQ] All CIF sequences completed")
        seq_logger.info("[VSEQ] Static random traffic virtual sequence done")


# ============================================================
# Static test implementation
# ============================================================
@pyuvm.test()
class cl_marb_tb_static_test(cl_marb_tb_base_test):
    """
    A4.1 Random traffic test with STATIC priority

    - Reuses A3 base environment (APB + 3x CIF + MIF + virtual sequencer)
    - Use APB to configure arbiter to STATIC mode (mode=0, enable=1)
    - Launch CIF0/1/2 random traffic via virtual sequence
    - Overlapping address window creates contention
    - Expected behavior:
        * Higher-priority CIF0 tends to be serviced more often
        * No multiple CIFs ack at the same time
    """

    def __init__(self, name="cl_marb_tb_static_test", parent=None):
        super().__init__(name, parent)

    async def run_phase(self):
        self.raise_objection()
        self.logger.info("[RUN] Starting MARB STATIC random test run_phase()")

        await self.start_clock()
        await self.trigger_reset()

        vseq = cl_marb_static_vseq("static_vseq")

        self.logger.info("Starting static virtual sequence on env.virtual_sequencer")
        await vseq.start(self.marb_tb_env.virtual_sequencer)

        # Wait a bit to allow remaining handshakes/acks to settle
        await Timer(100, units="ns")

        self.logger.info("STATIC random test completed")
        self.drop_objection()
