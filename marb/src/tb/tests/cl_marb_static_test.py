import cocotb
import random
import pyuvm
from pyuvm import *
from cocotb.triggers import Timer
from cl_marb_tb_base_test import cl_marb_tb_base_test


@pyuvm.test()
class cl_marb_static_test(cl_marb_tb_base_test):
    """A4.1 - Random traffic test with static priority"""

    async def run_phase(self):
        self.logger.info(f"APB agent class: {inspect.getfile(type(env.apb_agent))}")
        self.logger.info(f"CIF0 agent class: {inspect.getfile(type(env.sdt_cif_agents[0]))}")
        self.logger.info("▶️ [RUN] Starting MARB static priority test")
        await super().run_phase()

        # ============================================================
        # 1. Raise objection (keep simulation alive)
        # ============================================================
        self.raise_objection()
        env = self.marb_tb_env

        # ============================================================
        # 2. Enable MARB through APB register write
        # ============================================================
        self.logger.info("📝 Enabling MARB via APB control register (static mode)")
        apb_seqr = env.apb_agent.sequencer

        # 创建 APB 写事务（使能 + static mode）
        ctrl_item = env.apb_agent.driver.create_item()
        ctrl_item.addr = 0x00       # control register address
        ctrl_item.data = 0x1        # bit0: enable=1, bit1: mode=0 (static)
        ctrl_item.kind = "WRITE"

        await apb_seqr.start_item(ctrl_item)
        await apb_seqr.finish_item(ctrl_item)
        self.logger.info("✅ MARB Enabled (static mode)")

        # ============================================================
        # 3. Generate random SDT traffic from 3 CIFs
        # ============================================================
        num_tx = random.randint(5, 10)
        self.logger.info(f"📦 Generating {num_tx} random transactions per CIF")

        for i, agent in enumerate(env.sdt_cif_agents):
            self.logger.info(f"🚀 Starting CIF{i} random transactions")
            for _ in range(num_tx):
                seqr = agent.sequencer
                item = agent.driver.create_item()

                # 随机读写操作
                item.wr = random.choice([0, 1])
                item.rd = 1 - item.wr
                item.addr = random.randint(0, 15)
                item.wr_data = random.randint(0, 255)

                await seqr.start_item(item)
                await seqr.finish_item(item)

            self.logger.info(f"✅ CIF{i} finished sending {num_tx} transactions")

        # ============================================================
        # 4. Wait for arbitration & responses
        # ============================================================
        self.logger.info("⏳ Waiting 500ns for arbitration and acknowledgements...")
        await Timer(500, units="ns")

        # ============================================================
        # 5. Drop objection (end test)
        # ============================================================
        self.drop_objection()
        self.logger.info("🏁 [RUN] Finished MARB static priority test")
