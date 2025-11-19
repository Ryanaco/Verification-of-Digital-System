from pyuvm import *


class cl_marb_scoreboard(uvm_component):
    """Scoreboard comparing DUT output vs Reference Model output"""

    def __init__(self, name, parent):
        super().__init__(name, parent)

        # ✅ 改成 analysis_imp，这样 write() 会自动注册
        self.ref_export = uvm_analysis_imp("ref_export", self)
        self.dut_export = uvm_analysis_imp("dut_export", self)

        self.ref_queue = []
        self.dut_queue = []

    # ============================================================
    # Called automatically when connected analysis ports write
    # ============================================================
    def write_ref_export(self, txn):
        self.logger.info(
            f"📥 [SCOREBOARD] REF txn: CIF{getattr(txn, 'producer_id', '?')} "
            f"(addr={getattr(txn, 'addr', '?')}, data={getattr(txn, 'wr_data', '?')})"
        )
        self.ref_queue.append(txn)
        self._compare_if_ready()

    def write_dut_export(self, txn):
        self.logger.info(
            f"📥 [SCOREBOARD] DUT txn: CIF{getattr(txn, 'producer_id', '?')} "
            f"(addr={getattr(txn, 'addr', '?')}, data={getattr(txn, 'wr_data', '?')})"
        )
        self.dut_queue.append(txn)
        self._compare_if_ready()

    # ============================================================
    # Compare when both sides ready
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
