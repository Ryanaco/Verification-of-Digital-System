from pyuvm import *
import cocotb
from cocotb.triggers import Timer
from cl_marb_tb_base_test import cl_marb_tb_base_test
from vseqs.cl_marb_basic_seq import cl_marb_basic_seq
import random


class cl_marb_static_test(cl_marb_tb_base_test):
    """
    A4.1 Random traffic test with static priority
    """

    def __init__(self, name, parent):
        super().__init__(name, parent)

    def build_phase(self):
        """构建测试环境"""
        super().build_phase()
        self.logger.info("Start build_phase() -> MARB static test")
        self.logger.info("End build_phase() -> MARB static test")

    async def reset_dut(self):
        """🔄 DUT reset implementation"""
        dut = cocotb.top
        self.logger.info("Applying DUT reset...")
        dut.rst.value = 1
        await Timer(20, units="ns")
        dut.rst.value = 0
        self.logger.info("DUT reset complete.")

    async def run_phase(self):
        """主测试阶段"""
        self.raise_objection()
        self.logger.info("Start run_phase() -> MARB static test")

        await super().run_phase()
        await self.reset_dut()

        # ✅ 获取 environment 对象
        uvm_top = uvm_root()
        test_top = uvm_top.get_child("uvm_test_top")
        env = test_top.get_child("marb_tb_env") if test_top else None

        if env is None:
            raise RuntimeError("❌ Could not get marb_tb_env from hierarchy tree")

        self.logger.info("✅ Got MARB test environment object successfully.")

        # ✅ 正确寄存器访问（参数顺序：map, adapter, value）
        ctrl_reg = env.reg_model.ctrl_reg
        reg_map = env.reg_model.default_map

        await ctrl_reg.write(reg_map, env.adapter, 0x1, check=False)
        val = await ctrl_reg.read(reg_map, env.adapter, check=False)
        self.logger.info(f"Control reg after write: {val.value}")

        # 执行基础虚拟序列
        base_seq = cl_marb_basic_seq("base_seq")
        await base_seq.start(env.virtual_sequencer)

        # 生成随机 SDT traffic
        n_tx = random.randint(5, 10)
        self.logger.info(f"Generating {n_tx} random SDT requests per CIF")

        for _ in range(n_tx):
            for idx, agent in enumerate(env.sdt_cif_agents):
                seq_item = agent.sequencer.create_item()
                seq_item.rd = random.choice([0, 1])
                seq_item.wr = 1 - seq_item.rd
                seq_item.addr = random.randint(0, 0xFF)
                seq_item.wr_data = random.randint(0, 0xFFFF)
                await agent.sequencer.start_item(seq_item)
                await agent.sequencer.finish_item(seq_item)
            await Timer(10, units="ns")

        await Timer(1000, units="ns")
        self.logger.info("End run_phase() -> MARB static test")
        self.drop_objection()


@cocotb.test()
async def run_test(dut):
    """Cocotb entrypoint"""
    await uvm_root().run_test("cl_marb_static_test")
