import cocotb
from cocotb.triggers import ClockCycles
import pyuvm
from pyuvm import *

from cl_marb_tb_base_test import cl_marb_tb_base_test


@pyuvm.test()
class cl_marb_a9_violation_test(cl_marb_tb_base_test):

    async def run_phase(self):
        # 自己控制 objection，避免调用 super().run_phase() 把仿真直接跑完
        self.raise_objection()
        self.logger.info("⚠️ [A9 TEST] 强制制造 ACK 冲突，用于验证 A9 checker 是否生效")

        # 只复用 base_test 里的时钟和复位函数
        await self.start_clock()
        await self.trigger_reset()

        # 等一小段时间，确保 env / monitor / A7&A9 checkers 都已经启动
        await ClockCycles(self.dut.clk, 10)

        self.logger.critical("⚠️ [A9 TEST] 拉高 test_force_multi_ack 制造多重 ACK 冲突")
        self.dut.test_force_multi_ack.value = 1

        # 一拍就够触发
        await ClockCycles(self.dut.clk, 1)

        # 再拉回 0，避免后面全程都在报错
        self.dut.test_force_multi_ack.value = 0

        # 多跑几拍让 checker 有机会报 AssertionError
        await ClockCycles(self.dut.clk, 5)

        self.logger.critical("❌ [A9 TEST] 如果 ACK Checker 正常，此时应已经抛出 AssertionError")
        self.drop_objection()
