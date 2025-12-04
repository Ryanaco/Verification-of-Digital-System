import cocotb
from cocotb.triggers import ClockCycles, Timer
import pyuvm
from pyuvm import *

from cl_marb_tb_base_test import cl_marb_tb_base_test
from cocotb.handle import Force, Release
from uvc.sdt.src.sdt_if_assertions import SDTProtocolChecker
from cl_marb_ack_checker import MarbAckChecker


@pyuvm.test()
class cl_marb_a9_violation_test(cl_marb_tb_base_test):

    async def run_phase(self):
        self.raise_objection()
        self.logger.info("[RUN] Starting A9 Violation Test")

        # --- Reuse base_test logic to start clock, reset, and checkers ---
        # 1. Start clock and reset
        await self.start_clock()
        await self.trigger_reset()

        # 2. Start ACK Checker and SDT Protocol Checkers
        self.logger.critical("[A9 TEST] Starting checkers...")
        ack_checker = MarbAckChecker(
            "ack_checker",
            self.cfg.sdt_cif_cfgs[0].vif, self.cfg.sdt_cif_cfgs[1].vif,
            self.cfg.sdt_cif_cfgs[2].vif, self.cfg.sdt_mif_cfg.vif
        )
        cocotb.start_soon(ack_checker.start())
        # (Other checkers can be started here if needed)

        # 3. Wait several cycles to ensure checkers are running
        await ClockCycles(self.dut.clk, 5)

        # --- Inject A9 conflict ---
        self.logger.critical("[A9 TEST] FORCING multiple ACK signals")
        self.dut.c0_ack <= Force(1)
        self.dut.c1_ack <= Force(1)

        # Wait one cycle so checker can detect violation
        await ClockCycles(self.dut.clk, 1)

        # Release forced signals
        self.dut.c0_ack <= Release()
        self.dut.c1_ack <= Release()

        # Small delay to allow error messages to print fully
        await Timer(50, "ns")

        self.logger.info("[A9 TEST] Violation test finished. Checker should have fired.")
        # Note: We do NOT drop objection here.
        # If the checker behaves as expected, it will raise AssertionError,
        # causing the test to fail immediately — which is the intended behavior.
        # If the checker does NOT report an error, the test will time out
        # due to objection not being dropped, also indicating test failure.
