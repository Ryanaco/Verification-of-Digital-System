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
        self.logger.info("▶️ [RUN] Starting A9 Violation Test")

        # --- 复用 base_test 的逻辑来启动时钟、复位和检查器 ---
        # 1. 启动时钟和复位
        await self.start_clock()
        await self.trigger_reset()

        # 2. 启动 ACK Checker 和 SDT Protocol Checkers
        self.logger.critical("🔍 [A9 TEST] Starting checkers...")
        ack_checker = MarbAckChecker(
            "ack_checker",
            self.cfg.sdt_cif_cfgs[0].vif, self.cfg.sdt_cif_cfgs[1].vif,
            self.cfg.sdt_cif_cfgs[2].vif, self.cfg.sdt_mif_cfg.vif
        )
        cocotb.start_soon(ack_checker.start())
        # (其他 checkers 如果需要也可以在这里启动)

        # 3. 等待几个周期，确保 checker 已经运行
        await ClockCycles(self.dut.clk, 5)

        # --- 注入 A9 冲突 ---
        self.logger.critical("⚠️ [A9 TEST] FORCE 多重 ACK 冲突")
        self.dut.c0_ack <= Force(1)
        self.dut.c1_ack <= Force(1)

        # 等待一个周期让 checker 捕获
        await ClockCycles(self.dut.clk, 1)

        # 释放强制信号
        self.dut.c0_ack <= Release()
        self.dut.c1_ack <= Release()

        # 等待一小段时间，确保错误信息能够被完整打印
        await Timer(50, "ns")

        self.logger.info("🏁 [A9 TEST] Violation test finished. Checker should have fired.")
        # 注意：我们不在这里 drop_objection()。
        # 因为如果 checker 按预期工作，它会抛出 AssertionError，
        # 这会中断测试并报告为 FAIL，这正是我们想要的。
        # 如果 checker 没有报错，测试会因为 objection 未撤销而超时，
        # 这同样表明测试失败（因为预期的错误没有发生）。
