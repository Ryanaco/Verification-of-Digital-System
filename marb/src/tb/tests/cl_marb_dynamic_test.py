# File: src/tb/tests/cl_marb_dynamic_test.py
from pyuvm import *
import cocotb
from cl_marb_tb_base_test import cl_marb_tb_base_test
from vseqs.cl_marb_basic_seq import cl_marb_basic_seq
import random


@uvm_component_utils
class cl_marb_dynamic_test(cl_marb_tb_base_test):
    def __init__(self, name, parent):
        super().__init__(name, parent)

    async def run_phase(self):
        self.logger.info("Start run_phase() -> MARB dynamic test")
        await super().run_phase()

        # 1️⃣ 启动 clock & reset
        cocotb.start_soon(self.start_clock())
        await self.reset_dut()

        reg_model = self.env.reg_model

        # 2️⃣ 禁用仲裁（enable=0, mode=0）
        ctrl_reg = reg_model.ctrl_reg
        await ctrl_reg.write(self.env.adapter, 0x0)
        self.logger.info("Arbitration disabled")

        # 3️⃣ 随机设置动态优先级
        dprio_reg = reg_model.dprio_reg
        prio_c0 = random.randint(0, 255)
        prio_c1 = random.randint(0, 255)
        prio_c2 = random.randint(0, 255)
        dprio_value = (prio_c2 << 16) | (prio_c1 << 8) | prio_c0
        await dprio_reg.write(self.env.adapter, dprio_value)
        self.logger.info(f"Dynamic priorities set: C0={prio_c0}, C1={prio_c1}, C2={prio_c2}")

        # 4️⃣ 等待 sorting 完成（6 cycles）
        await Timer(6 * 3, units="ns")

        # 5️⃣ 启用仲裁 + 动态模式（enable=1, mode=1）
        ctrl_value = (1 << 0) | (1 << 1)
        await ctrl_reg.write(self.env.adapter, ctrl_value)
        self.logger.info("Arbitration re-enabled (dynamic mode)")

        # 6️⃣ 启动基础寄存器初始化序列
        base_seq = cl_marb_basic_seq("base_seq")
        await base_seq.start(self.env.virtual_sequencer)

        # 7️⃣ 生成随机请求流量
        n_tx = random.randint(5, 10)
        self.logger.info(f"Generating {n_tx} random SDT requests per CIF")

        for i in range(n_tx):
            for idx, agent in enumerate(self.env.sdt_cif_agents):
                seq_item = agent.sequencer.create_item()
                seq_item.rd = random.choice([0, 1])
                seq_item.wr = 1 - seq_item.rd
                seq_item.addr = random.randint(0, 0xFF)
                seq_item.wr_data = random.randint(0, 0xFFFF)
                await agent.sequencer.start_item(seq_item)
                await agent.sequencer.finish_item(seq_item)

            await Timer(10, units="ns")

        self.logger.info("End run_phase() -> MARB dynamic test")
