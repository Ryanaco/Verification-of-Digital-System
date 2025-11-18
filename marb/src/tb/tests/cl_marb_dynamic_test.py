import cocotb
import random
import pyuvm
from pyuvm import *
from cocotb.triggers import Timer
from cl_marb_tb_base_test import cl_marb_tb_base_test

from uvc.apb.src.cl_apb_seq_item import cl_apb_seq_item


@pyuvm.test()
class cl_marb_dynamic_test(cl_marb_tb_base_test):
    """A4.2 - Random traffic test with dynamic priority (simplified version)"""

    async def run_phase(self):
        self.logger.info("▶️ [RUN] Starting MARB dynamic priority test")

        self.raise_objection()
        await super().run_phase()

        env = self.marb_tb_env
        apb_seqr = env.apb_agent.sequencer

        # ============================================================
        # Enable MARB (dynamic mode)
        # ============================================================
        ctrl_item = cl_apb_seq_item("ctrl_item")
        ctrl_item.addr = 0x00
        ctrl_item.data = 0x3  # enable=1, mode=1
        ctrl_item.kind = "WRITE"
        await apb_seqr.start_item(ctrl_item)
        await apb_seqr.finish_item(ctrl_item)
        self.logger.info("✅ MARB Enabled (dynamic mode)")

        # ============================================================
        # Dynamic priority updates only
        # ============================================================
        for update_step in range(3):
            new_prio = random.sample([0, 1, 2], 3)
            prio_data = (new_prio[0] << 4) | (new_prio[1] << 2) | new_prio[2]

            prio_item = cl_apb_seq_item(f"prio_item_{update_step}")
            prio_item.addr = 0x04
            prio_item.data = prio_data
            prio_item.kind = "WRITE"

            await apb_seqr.start_item(prio_item)
            await apb_seqr.finish_item(prio_item)
            self.logger.info(
                f"🔄 Updated priority order -> CIF0:{new_prio[0]} CIF1:{new_prio[1]} CIF2:{new_prio[2]}"
            )

            await Timer(200, units="ns")

        # ============================================================
        # Wait + end test
        # ============================================================
        self.logger.info("⏳ Waiting 500ns for arbitration after priority updates...")
        await Timer(500, units="ns")

        self.drop_objection()
        self.logger.info("✅ MARB dynamic priority test finished successfully.")
