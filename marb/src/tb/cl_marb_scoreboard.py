from pyuvm import *


class RefSubscriber(uvm_subscriber):
    """Subscriber to receive Reference Model outputs"""
    def __init__(self, name, parent):
        super().__init__(name, parent)

    def write(self, txn):
        """Called when ref_model writes to analysis port"""
        self.logger.info(
            f"📥 [SCOREBOARD] REF txn: CIF{getattr(txn, 'producer_id', '?')} "
            f"(addr={getattr(txn, 'addr', '?')}, data={getattr(txn, 'wr_data', '?')})"
        )
        # Send to scoreboard for comparison
        if hasattr(self.get_parent(), '_process_ref_txn'):
            self.get_parent()._process_ref_txn(txn)


class DutSubscriber(uvm_subscriber):
    """Subscriber to receive DUT (MIF) outputs"""
    def __init__(self, name, parent):
        super().__init__(name, parent)

    def write(self, txn):
        """Called when MIF monitor writes to analysis port"""
        self.logger.info(
            f"📥 [SCOREBOARD] DUT txn: CIF{getattr(txn, 'producer_id', '?')} "
            f"(addr={getattr(txn, 'addr', '?')}, data={getattr(txn, 'wr_data', '?')})"
        )
        # Send to scoreboard for comparison
        if hasattr(self.get_parent(), '_process_dut_txn'):
            self.get_parent()._process_dut_txn(txn)


class cl_marb_scoreboard(uvm_component):
    """Scoreboard comparing DUT and Reference Model outputs"""

    def __init__(self, name, parent):
        super().__init__(name, parent)
        
        # Create subscribers
        self.ref_subscriber = None
        self.dut_subscriber = None

        self.ref_queue = []
        self.dut_queue = []

    def build_phase(self):
        super().build_phase()
        # Create subscribers during build phase
        self.ref_subscriber = RefSubscriber("ref_subscriber", self)
        self.dut_subscriber = DutSubscriber("dut_subscriber", self)

    # ============================================================
    # Process transactions from subscribers
    # ============================================================
    def _process_ref_txn(self, txn):
        """Handle Reference Model transaction"""
        self.ref_queue.append(txn)
        self._compare_if_ready()

    def _process_dut_txn(self, txn):
        """Handle DUT transaction"""
        self.dut_queue.append(txn)
        self._compare_if_ready()

    # ============================================================
    # 比较两边事务
    # ============================================================
    def _compare_if_ready(self):
        if not self.ref_queue or not self.dut_queue:
            return

        ref_txn = self.ref_queue.pop(0)
        dut_txn = self.dut_queue.pop(0)

        ref_id = getattr(ref_txn, "producer_id", None)
        dut_id = getattr(dut_txn, "producer_id", None)
        ref_addr = getattr(ref_txn, "addr", None)
        dut_addr = getattr(dut_txn, "addr", None)
        ref_data = getattr(ref_txn, "wr_data", None)
        dut_data = getattr(dut_txn, "wr_data", None)

        if (ref_id == dut_id) and (ref_addr == dut_addr) and (ref_data == dut_data):
            self.logger.info(f"✅ [MATCH] CIF{ref_id} OK (addr={ref_addr}, data={ref_data})")
        else:
            self.logger.error(
                f"❌ [MISMATCH] REF: CIF{ref_id}, addr={ref_addr}, data={ref_data} "
                f"≠ DUT: CIF{dut_id}, addr={dut_addr}, data={dut_data}"
            )
