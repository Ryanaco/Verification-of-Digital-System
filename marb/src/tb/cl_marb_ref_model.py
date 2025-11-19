from pyuvm import *


class cl_marb_ref_model(uvm_subscriber):
    """
    A5 Reference Model for MARB (Memory Arbiter)
    """

    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.ref_ap = uvm_analysis_port("ref_ap", self)
        self.config = None
        self.pending_reqs = []

    def build_phase(self):
        """Retrieve configuration and initialize"""
        self.logger.info("🧠 [BUILD] Building MARB Reference Model")

        try:
            # ✅ 从全局 ConfigDB 获取配置（保证找到）
            self.config = ConfigDB().get(None, "marb_tb_env", "cfg")
            if self.config is not None:
                self.logger.info("✅ [BUILD] Reference Model got cfg successfully")
            else:
                self.logger.warning("⚠️ ConfigDB returned None, using default config.")
        except Exception as e:
            # ✅ 捕获任何异常，防止 cocotb 崩溃
            self.logger.warning(f"⚠️ Could not find cfg in ConfigDB: {e}")
            self.config = None

    def write(self, txn):
        """Receive transactions from SDT CIF request_ap"""
        if txn is None:
            self.logger.warning("⚠️ Received None txn, ignoring")
            return

        try:
            cid = getattr(txn, "producer_id", "?")
            addr = getattr(txn, "addr", "?")
            self.logger.debug(f"📥 [REF MODEL] CIF{cid} request addr={addr}")
            self.pending_reqs.append(txn)

            # Perform arbitration when 3 requests collected
            if len(self.pending_reqs) >= 3:
                winner = self._perform_arbitration(self.pending_reqs)
                self.logger.info(
                    f"🏆 [REF MODEL] Winner: CIF{winner.producer_id} (addr={winner.addr})"
                )
                self.ref_ap.write(winner)
                self.pending_reqs.clear()
        except Exception as e:
            self.logger.error(f"❌ Exception in ref_model.write(): {e}")

    def _perform_arbitration(self, req_list):
        """Static or dynamic arbitration"""
        try:
            if self.config is None:
                self.logger.debug("⚙️ No config, fallback to static order.")
                return sorted(req_list, key=lambda r: getattr(r, "producer_id", 0))[0]

            mode = getattr(self.config, "mode", "static")
            if mode == "static":
                sorted_reqs = sorted(req_list, key=lambda r: getattr(r, "producer_id", 0))
            else:
                prio_order = getattr(self.config, "dynamic_prio", [0, 1, 2])
                sorted_reqs = sorted(req_list, key=lambda r: prio_order.index(r.producer_id))

            return sorted_reqs[0]
        except Exception as e:
            self.logger.error(f"❌ Arbitration error: {e}")
            return req_list[0]
