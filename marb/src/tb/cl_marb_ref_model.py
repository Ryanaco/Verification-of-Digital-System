# cl_marb_ref_model.py
import logging
from collections import deque

import pyuvm
from pyuvm import *

from uvc.sdt.src import *                 # cl_sdt_seq_item
from uvc.apb.src import *                 # cl_apb_seq_item
from uvc.apb.src.apb_common import OpType # RD / WR


# ============================================================
# Register addresses / encoding (must match RTL and tests)
# ============================================================
ARB_MODE_ADDR = 0x00  # control register
C0_PRIO_ADDR  = 0x04  # CIF0 dynamic priority
C1_PRIO_ADDR  = 0x08  # CIF1 dynamic priority
C2_PRIO_ADDR  = 0x0C  # CIF2 dynamic priority

# Control register encoding
MODE_STATIC  = 0
MODE_DYNAMIC = 1
ENABLE_OFF   = 0
ENABLE_ON    = 1


class cl_marb_ref_model(uvm_subscriber):
    """
    Memory Arbiter Reference Model (A5)

    - Inherits from uvm_subscriber:
        * input via analysis_export:
            - Receives SDT request transactions from CIF0/1/2 (from request_ap)
            - Receives APB configuration transactions (from apb_monitor.ap)
        * output via ref_ap:
            - Sends the arbitration winner transaction (golden reference) to the Scoreboard

    Behavior:
        * Maintains control register: enable, mode (static/dynamic)
        * Maintains dynamic priority registers: each CIF has one 8-bit priority (larger = higher)
        * Maintains a pending request queue for each CIF
        * Whenever a new request arrives, uses mode + priority to determine the winner
        * Sends the winner transaction to the Scoreboard via ref_ap
    """

    def __init__(self, name="cl_marb_ref_model", parent=None):
        super().__init__(name, parent)

        # Output port to Scoreboard
        self.ref_ap = uvm_analysis_port("ref_ap", self)

        # ====== Arbiter configuration state ======
        self.enable = ENABLE_OFF
        self.mode   = MODE_STATIC

        # Dynamic priority registers (higher value = higher priority)
        # Index = CIF ID (0,1,2)
        self.dprio_vals = [0, 0, 0]

        # ====== Pending request queues for each CIF ======
        # Each element is a cl_sdt_seq_item
        self.pending = {
            0: deque(),
            1: deque(),
            2: deque(),
        }

        self.logger = logging.getLogger("MARB_REF_MODEL")

    # ============================================================
    # Top-level write(): receives all TLM transactions
    #   - From CIF request_ap: SDT items
    #   - From APB monitor: APB items
    # ============================================================
    def write(self, item):
        """
        TLM write() entry point.

        - If APB transaction: update control/priority registers
        - If SDT transaction: enqueue request and attempt arbitration
        """
        if isinstance(item, cl_apb_seq_item):
            self._handle_apb(item)
            return

        if isinstance(item, cl_sdt_seq_item):
            self._handle_cif_request(item)
            return

        self.logger.warning(
            f"[REF MODEL] Received unsupported item type: {type(item)} -> {item}"
        )

    # ============================================================
    # Handle APB configuration transactions
    # ============================================================
    def _handle_apb(self, apb_item: cl_apb_seq_item):
        """
        Processes register configuration input:
        - ctrl register @ 0x00
        - dprio registers @ 0x04, 0x08, 0x0C
        Processes only write operations.
        """
        op = getattr(apb_item, "op", None)
        if op != OpType.WR:
            return

        addr = int(apb_item.addr)
        data = int(apb_item.data)

        if addr == ARB_MODE_ADDR:
            self.enable = data & 0x1
            self.mode   = (data >> 1) & 0x3

            self.logger.info(
                f"[REF MODEL] CTRL updated: enable={self.enable}, mode={self.mode}"
            )

        elif addr == C0_PRIO_ADDR:
            self.dprio_vals[0] = data & 0xFF
            self.logger.info(f"[REF MODEL] dprio[C0] = {self.dprio_vals[0]}")

        elif addr == C1_PRIO_ADDR:
            self.dprio_vals[1] = data & 0xFF
            self.logger.info(f"[REF MODEL] dprio[C1] = {self.dprio_vals[1]}")

        elif addr == C2_PRIO_ADDR:
            self.dprio_vals[2] = data & 0xFF
            self.logger.info(f"[REF MODEL] dprio[C2] = {self.dprio_vals[2]}")

        # Arbitration is not triggered here; it happens when a request arrives.

    # ============================================================
    # Handle CIF SDT request transactions
    # ============================================================
    def _handle_cif_request(self, item: cl_sdt_seq_item):
        """
        Stimulus from CIF request_ap.

        CIF ID determination:
          - Prefer item.cif_id or item.client_id (added by monitor)
          - If missing, default to CIF0 and emit warning
        """
        if hasattr(item, "cif_id"):
            cid = int(item.cif_id)
        elif hasattr(item, "client_id"):
            cid = int(item.client_id)
        else:
            cid = 0
            self.logger.warning(
                f"[REF MODEL] SDT item has no cif_id/client_id; defaulting to CIF0: item={item}"
            )

        if cid not in (0, 1, 2):
            self.logger.warning(
                f"[REF MODEL] Unexpected CIF id {cid}; ignoring item={item}"
            )
            return

        self.pending[cid].append(item)

        self.logger.debug(
            f"[REF MODEL] Request from CIF{cid}: "
            f"addr=0x{int(item.addr):02X}, access={int(item.access)}, data=0x{int(item.data):02X}"
        )

        self._maybe_arbitrate()

    # ============================================================
    # Compute current priority order
    # ============================================================
    def _current_priority_order(self):
        """
        Returns a list of CIF IDs sorted by current priority.

        - static: fixed [0,1,2] (CIF0 > CIF1 > CIF2)
        - dynamic: sorted by dprio (higher first), break ties by smaller CIF ID
        """
        if self.mode == MODE_STATIC:
            return [0, 1, 2]

        ids = [0, 1, 2]
        ids.sort(key=lambda cid: (-self.dprio_vals[cid], cid))
        return ids

    # ============================================================
    # Arbitration core logic
    # ============================================================
    def _maybe_arbitrate(self):
        """
        If arbiter is enabled and pending requests exist,
        select a winner and send it to the Scoreboard.
        """
        if self.enable != ENABLE_ON:
            return

        order = self._current_priority_order()

        winner_cid = None
        for cid in order:
            if self.pending[cid]:
                winner_cid = cid
                break

        if winner_cid is None:
            return

        item = self.pending[winner_cid].popleft()

        setattr(item, "cif_id", winner_cid)

        addr   = int(item.addr)
        data   = int(item.data)
        access = int(item.access)

        self.logger.info(
            f"[REF MODEL] Winner: CIF{winner_cid} "
            f"(addr={addr}, access={access}, data=0x{data:02X})"
        )

        self.ref_ap.write(item)

    # ============================================================
    # final_phase: optional reporting of pending requests
    # ============================================================
    def final_phase(self):
        super().final_phase()
        total_pending = sum(len(q) for q in self.pending.values())
        if total_pending > 0:
            self.logger.warning(
                f"[REF MODEL] final_phase: {total_pending} pending requests remain in queues"
            )
