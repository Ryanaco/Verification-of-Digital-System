import cocotb
import random
import pyuvm
from pyuvm import *
from cocotb.triggers import Timer
from cl_marb_tb_base_test import cl_marb_tb_base_test
from uvc.apb.src.cl_apb_seq_item import cl_apb_seq_item
from uvc.apb.src.apb_common import OpType
from uvc.sdt.src.cl_sdt_seq_item import cl_sdt_seq_item


@pyuvm.test()
class cl_marb_dynamic_test(cl_marb_tb_base_test):
    """A4.2 - Random traffic test with dynamic priority"""

    async def run_phase(self):
        self.logger.info("▶️ [RUN] Starting MARB dynamic priority test")

        self.raise_objection()
        await super().run_phase()

        env = self.marb_tb_env
        self.logger.info(f"Environment ready: {len(env.sdt_cif_agents)} CIFs + 1 MIF")
        
        # Wait for driver initialization
        await Timer(100, units="ns")

        # ============================================================
        # 1️⃣ Enable MARB (dynamic mode)
        # ============================================================
        self.logger.info("📝 Enabling MARB via APB control register (dynamic mode)")
        apb_seqr = env.apb_agent.sequencer

        ctrl_item = cl_apb_seq_item("ctrl_item")
        ctrl_item.addr = 0x00
        ctrl_item.data = 0x3   # bit0: enable=1, bit1: mode=1 (dynamic)
        ctrl_item.op = OpType.WR

        await apb_seqr.start_item(ctrl_item)
        await apb_seqr.finish_item(ctrl_item)
        self.logger.info("✅ MARB Enabled (dynamic mode)")

        # ============================================================
        # 2️⃣ Random traffic generation
        # ============================================================
        num_tx = random.randint(5, 10)
        self.logger.info(f"📦 Generating {num_tx} random transactions per CIF")

        for i, agent in enumerate(env.sdt_cif_agents):
            self.logger.info(f"🚀 Starting CIF{i} random transactions")

            for j in range(num_tx):
                item = cl_sdt_seq_item.create(f"cif{i}_item{j}")
                item.access = random.choice([0, 1])  # 0=READ, 1=WRITE
                item.addr = random.randint(0, 15)
                item.data = random.randint(0, 255)

                await agent.sequencer.start_item(item)
                await agent.sequencer.finish_item(item)

            self.logger.info(f"✅ CIF{i} finished sending {num_tx} transactions")

        # ============================================================
        # 3️⃣ Change priorities dynamically
        # ============================================================
        self.logger.info("🔁 Updating MARB priority register dynamically...")

        for update_step in range(3):
            new_prio = random.sample([0, 1, 2], 3)
            prio_data = (new_prio[0] << 4) | (new_prio[1] << 2) | new_prio[2]

            prio_item = cl_apb_seq_item(f"prio_item_{update_step}")
            prio_item.addr = 0x04
            prio_item.data = prio_data
            prio_item.op = OpType.WR

            await apb_seqr.start_item(prio_item)
            await apb_seqr.finish_item(prio_item)

            self.logger.info(f"🔄 Updated priority order -> CIF0:{new_prio[0]} CIF1:{new_prio[1]} CIF2:{new_prio[2]}")
            await Timer(200, units="ns")

        self.logger.info("⏳ Waiting 500ns for arbitration after priority updates...")
        await Timer(500, units="ns")

        self.logger.info("🏁 [RUN] Test completed, dropping objection...")
        self.drop_objection()
        self.logger.info("✅ MARB dynamic priority test finished successfully.")
