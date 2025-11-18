from pyuvm import *


class cl_marb_ref_model(uvm_subscriber):
    """
    A5 Reference Model for MARB (Memory Arbiter)
    ------------------------------------------------------------
    - Receives CIF requests through request_ap ports.
    - Models arbitration (static or dynamic) to produce
      golden reference transactions.
    - Sends golden outputs to the Scoreboard for comparison.
    """

    def __init__(self, name, parent):
        super().__init__(name, parent)
        # Output analysis port for scoreboard connection
        self.ref_ap = uvm_analysis_port("ref_ap", self)

        # Internal state
        self.config = None
        self.pending_reqs = []  # collected CIF requests

    # ============================================================
    # BUILD PHASE
    # ============================================================
    def build_phase(self):
        """Retrieve configuration and initialize model"""
        self.logger.info("🧠 [BUILD] Building MARB Reference Model")

        try:
            # ✅ FIX: Use relative path ("..") to get cfg from parent (env)
            self.config = ConfigDB().get(self, "..", "cfg")
            self.logger.info("✅ [BUILD] Reference Model got cfg successfully")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not find cfg in ConfigDB: {e}")
            self.config = None

    # ============================================================
    # WRITE FUNCTION (receives CIF requests)
    # ============================================================
    def write(self, txn):
        """
        Triggered automatically when a CIF producer agent
        broadcasts a request transaction via request_ap.
        """
        cid = getattr(txn, "producer_id", "?")
        addr = getattr(txn, "addr", "?")
        self.logger.debug(f"📥 [REF MODEL] Received request from CIF{cid} (addr={addr})")

        # Store transaction
        self.pending_reqs.append(txn)

        # Once all CIFs have requested, perform arbitration
        if len(self.pending_reqs) >= 3:
            winner = self._perform_arbitration(self.pending_reqs)
            self.logger.info(
                f"🏆 [REF MODEL] Winner: CIF{winner.producer_id} (addr={winner.addr})"
            )

            # Send golden result to scoreboard
            self.ref_ap.write(winner)
            self.pending_reqs.clear()

    # ============================================================
    # ARBITRATION LOGIC
    # ============================================================
    def _perform_arbitration(self, req_list):
        """
        Decide which CIF wins arbitration.
        Supports static and dynamic modes based on configuration.
        """

        if self.config is None:
            self.logger.warning("⚠️ No config found, defaulting to static priority")
            sorted_reqs = sorted(req_list, key=lambda r: getattr(r, "producer_id", 0))
            return sorted_reqs[0]

        # Detect mode (static/dynamic)
        mode = getattr(self.config, "mode", "static")
        self.logger.debug(f"🔍 [REF MODEL] Arbitration mode = {mode}")

        if mode == "static":
            # Static mode: CIF0 > CIF1 > CIF2
            sorted_reqs = sorted(req_list, key=lambda r: getattr(r, "producer_id", 0))

        else:
            # Dynamic mode: Use config’s dynamic priority order
            prio_order = getattr(self.config, "dynamic_prio", [0, 1, 2])
            self.logger.debug(f"🔢 [REF MODEL] Dynamic priority = {prio_order}")
            sorted_reqs = sorted(req_list, key=lambda r: prio_order.index(r.producer_id))

        return sorted_reqs[0]
