import cocotb
from cocotb.triggers import RisingEdge
import logging


class MarbAckChecker:
    """
    A9: Memory Arbiter ACK legality checker

    Rules:
        - Only ONE CIF may assert ACK in any given cycle.
        - If 2 or more ACKs are HIGH simultaneously → protocol violation.
    """

    def __init__(self, name, vif_cif0, vif_cif1, vif_cif2, vif_mif):
        self.name = name
        self.vif_cif0 = vif_cif0
        self.vif_cif1 = vif_cif1
        self.vif_cif2 = vif_cif2
        self.vif_mif  = vif_mif

        self.logger = logging.getLogger(f"MARB_ACK_CHECKER.{name}")

    async def start(self):
        self.logger.info("[A9] ACK Checker started")
        cocotb.start_soon(self._check_ack_rules())

    async def _check_ack_rules(self):
        while True:
            await RisingEdge(self.vif_cif0.clk)

            ack0 = int(self.vif_cif0.ack.value)
            ack1 = int(self.vif_cif1.ack.value)
            ack2 = int(self.vif_cif2.ack.value)
            ackm = int(self.vif_mif.ack.value)   # For completeness — normally MIF should not ACK

            ack_sum = ack0 + ack1 + ack2

            # --- A9 Rule: only one CIF can receive ACK ---
            if ack_sum > 1:
                self.logger.error(
                    f" [A9] MULTIPLE ACKs DETECTED! "
                    f"CIF0={ack0}, CIF1={ack1}, CIF2={ack2}"
                )
                raise AssertionError("A9 violation: multiple CIFs acknowledged simultaneously")

            # Optional: ensure MIF never asserts ACK
            if ackm == 1:
                self.logger.warning("[A9] Warning: MIF ack=1 (unexpected in MARB)")
