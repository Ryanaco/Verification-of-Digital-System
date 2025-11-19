"""
A5: Scoreboard and Reference Model Verification Test
- Verifies that the reference model correctly predicts DUT arbitration
- Scoreboard compares reference model output with DUT output
"""

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
class cl_marb_scoreboard_test(cl_marb_tb_base_test):
    """A5 - Scoreboard and Reference Model Test"""

    async def run_phase(self):
        self.logger.info("▶️ [RUN] Starting MARB Scoreboard and Reference Model verification")

        self.raise_objection()
        await super().run_phase()

        env = self.marb_tb_env
        self.logger.info(f"✅ Environment ready with Scoreboard and Ref Model")
        
        # Wait for driver initialization
        await Timer(100, units="ns")

        # ============================================================
        # Enable MARB (static mode)
        # ============================================================
        self.logger.info("📝 Enabling MARB via APB control register")
        apb_seqr = env.apb_agent.sequencer

        ctrl_item = cl_apb_seq_item("ctrl_item")
        ctrl_item.addr = 0x00
        ctrl_item.data = 0x1   # bit0: enable=1, bit1: mode=0 (static)
        ctrl_item.op = OpType.WR

        await apb_seqr.start_item(ctrl_item)
        await apb_seqr.finish_item(ctrl_item)
        self.logger.info("✅ MARB Enabled (static mode)")

        # ============================================================
        # Test 1: Static priority with 3 concurrent requests
        # ============================================================
        self.logger.info("🧪 [TEST 1] Static Priority Test")
        
        for round_num in range(2):
            self.logger.info(f"  Round {round_num + 1}")
            
            # Send 1 request per CIF
            for i in range(3):
                cif_agent = env.sdt_cif_agents[i]
                item = cl_sdt_seq_item.create(f"cif{i}_item_r{round_num}")
                item.access = 1  # WRITE
                item.addr = 0x10 + i
                item.data = 0xAA + i
                
                await cif_agent.sequencer.start_item(item)
                await cif_agent.sequencer.finish_item(item)
            
            self.logger.info(f"  ✓ Round {round_num + 1} requests sent")
            await Timer(500, units="ns")
        
        # ============================================================
        # Final wait for scoreboard comparisons
        # ============================================================
        self.logger.info("⏳ Waiting for scoreboard to complete comparisons...")
        await Timer(1000, units="ns")
        
        self.logger.info("🏁 Test completed successfully")
        self.drop_objection()
