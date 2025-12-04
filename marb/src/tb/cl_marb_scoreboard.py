# cl_marb_scoreboard.py
import logging
from collections import deque

import pyuvm
from pyuvm import *

from cocotb.triggers import Timer
from uvc.sdt.src import *   # cl_sdt_seq_item


class _marb_ref_subscriber(uvm_subscriber):
    """
    Subscriber used by the Scoreboard to receive REF model output.
    """
    def __init__(self, name, parent, queue_ref):
        super().__init__(name, parent)
        self.queue_ref = queue_ref
        self.logger = logging.getLogger("MARB_SCOREBOARD_REF_SUB")

    def write(self, item: cl_sdt_seq_item):
        self.logger.info(
            f"[SCOREBOARD] REF txn: CIF{int(getattr(item, 'cif_id', -1))} "
            f"(addr={int(item.addr)}, data=0x{int(item.data):02X}, access={int(item.access)})"
        )
        self.queue_ref.append(item)


class _marb_dut_subscriber(uvm_subscriber):
    """
    Subscriber used by the Scoreboard to receive DUT output from MIF monitor.
    """
    def __init__(self, name, parent, queue_dut):
        super().__init__(name, parent)
        self.queue_dut = queue_dut
        self.logger = logging.getLogger("MARB_SCOREBOARD_DUT_SUB")

    def write(self, item: cl_sdt_seq_item):
        addr = int(item.addr)
        data = int(item.data)
        access = int(item.access)

        self.logger.info(
            f"[SCOREBOARD] DUT txn: addr={addr}, data=0x{data:02X}, access={access}"
        )
        self.queue_dut.append(item)


class cl_marb_scoreboard(uvm_component):
    """
    Memory Arbiter Scoreboard (A6)

    - ref_subscriber: receives golden transactions from ref_model.ref_ap
    - dut_subscriber: receives DUT transactions from MIF monitor.ap
    - When both sides have data, they are compared:
        * address
        * access type
        * data (only for write operations)
    - mismatch is reported using warnings; can be tightened to uvm_error if needed
    """

    def __init__(self, name="cl_marb_scoreboard", parent=None):
        super().__init__(name, parent)

        self.logger = logging.getLogger("MARB_SCOREBOARD")

        # Queues holding REF and DUT transactions
        self.ref_queue = deque()
        self.dut_queue = deque()

        # Subscribers bound by the environment
        self.ref_subscriber = _marb_ref_subscriber(
            "ref_subscriber", self, self.ref_queue
        )
        self.dut_subscriber = _marb_dut_subscriber(
            "dut_subscriber", self, self.dut_queue
        )

    def build_phase(self):
        super().build_phase()
        self.logger.info("[SCOREBOARD] Build phase")

    async def run_phase(self):
        """
        Intelligent matching:
        For each DUT transaction, attempt to find a matching REF transaction.
        Match condition:
            - Same address
            - Same access type
        Approach:
        - If DUT arrives and a matching REF exists → compare
        - If no matching REF exists but REF queue is non-empty → requeue DUT
        - If REF queue is empty → requeue DUT and wait
        """
        self.logger.info("[SCOREBOARD] Start run_phase()")
        pending_dut = deque()

        while True:
            await Timer(10, "ns")

            # Try matching previously unmatched DUT items
            if pending_dut and self.ref_queue:
                dut_item = pending_dut.popleft()
                matched_ref = self._find_matching_ref(dut_item)

                if matched_ref:
                    self._compare(matched_ref, dut_item)
                else:
                    pending_dut.append(dut_item)

            # Process new DUT items
            while self.dut_queue:
                dut_item = self.dut_queue.popleft()
                matched_ref = self._find_matching_ref(dut_item)

                if matched_ref:
                    self._compare(matched_ref, dut_item)
                else:
                    pending_dut.append(dut_item)

    def _find_matching_ref(self, dut_item):
        """Search REF queue for a matching reference item."""
        for ref_item in self.ref_queue:
            if (int(ref_item.addr) == int(dut_item.addr) and
                int(ref_item.access) == int(dut_item.access)):
                self.ref_queue.remove(ref_item)
                return ref_item
        return None

    # ===============================
    # Core comparison logic
    # ===============================
    def _compare(self, ref_item: cl_sdt_seq_item, dut_item: cl_sdt_seq_item):
        ref_addr = int(ref_item.addr)
        dut_addr = int(dut_item.addr)

        ref_data = int(ref_item.data)
        dut_data = int(dut_item.data)

        ref_access = int(ref_item.access)
        dut_access = int(dut_item.access)

        cif_id = int(getattr(ref_item, "cif_id", -1))

        # Address comparison
        if ref_addr != dut_addr:
            self.logger.warning(
                f"[SCOREBOARD] Address mismatch: "
                f"REF: CIF{cif_id} addr={ref_addr}, DUT addr={dut_addr}"
            )
            return

        # Access comparison
        if ref_access != dut_access:
            self.logger.warning(
                f"[SCOREBOARD] Access type mismatch: "
                f"REF: CIF{cif_id} access={ref_access}, DUT access={dut_access}"
            )
            return

        # Data comparison only for write operations
        if ref_access == 1:
            if ref_data != dut_data:
                self.logger.warning(
                    f"[SCOREBOARD] Write data mismatch: "
                    f"REF: CIF{cif_id} data=0x{ref_data:02X}, DUT data=0x{dut_data:02X}"
                )
                return

        self.logger.info(
            f"[SCOREBOARD] Match: CIF{cif_id}, "
            f"addr={ref_addr}, access={ref_access}, data=0x{ref_data:02X}"
        )
