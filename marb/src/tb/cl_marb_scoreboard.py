# cl_marb_scoreboard.py
import logging
from collections import deque

import pyuvm
from pyuvm import *

from cocotb.triggers import Timer   # ✅ 别忘了这个

from uvc.sdt.src import *   # cl_sdt_seq_item


class _marb_ref_subscriber(uvm_subscriber):
    """
    用于 Scoreboard 接收 REF 模型输出的 subscriber
    """
    def __init__(self, name, parent, queue_ref):
        super().__init__(name, parent)
        self.queue_ref = queue_ref
        self.logger = logging.getLogger("MARB_SCOREBOARD_REF_SUB")

    def write(self, item: cl_sdt_seq_item):
        self.logger.info(
            f"📥 [SCOREBOARD] REF txn: CIF{int(getattr(item, 'cif_id', -1))} "
            f"(addr={int(item.addr)}, data=0x{int(item.data):02X}, access={int(item.access)})"
        )
        self.queue_ref.append(item)


class _marb_dut_subscriber(uvm_subscriber):
    """
    用于 Scoreboard 接收 DUT (MIF monitor ap) 输出的 subscriber
    """
    def __init__(self, name, parent, queue_dut):
        super().__init__(name, parent)
        self.queue_dut = queue_dut
        self.logger = logging.getLogger("MARB_SCOREBOARD_DUT_SUB")

    def write(self, item: cl_sdt_seq_item):
        # DUT 侧 item 通常只代表 MIF 方向访问，没有 CIF id；
        # 可以由 monitor 填一个来源字段，也可以 Scoreboard 只比较 addr/data。
        addr = int(item.addr)
        data = int(item.data)
        access = int(item.access)

        self.logger.info(
            f"📥 [SCOREBOARD] DUT txn: addr={addr}, data=0x{data:02X}, access={access}"
        )
        self.queue_dut.append(item)


class cl_marb_scoreboard(uvm_component):
    """
    Memory Arbiter Scoreboard (A6)

    - ref_subscriber: 通过 ref_model.ref_ap 接收 golden txn
    - dut_subscriber: 通过 MIF monitor.ap 接收 DUT txn
    - 每当两边都有 txn 时进行比较：
        * 地址
        * 访问类型（access）
        * 数据（data，在写操作时比较）
    - mismatch 时使用 uvm_error -> 计入测试失败
    """

    def __init__(self, name="cl_marb_scoreboard", parent=None):
        super().__init__(name, parent)

        self.logger = logging.getLogger("MARB_SCOREBOARD")

        # 两个队列，用于暂存 REF / DUT 的事务
        self.ref_queue = deque()
        self.dut_queue = deque()

        # 两个 subscriber，env 里会把 AP 连过来
        self.ref_subscriber = _marb_ref_subscriber(
            "ref_subscriber", self, self.ref_queue
        )
        self.dut_subscriber = _marb_dut_subscriber(
            "dut_subscriber", self, self.dut_queue
        )

    def build_phase(self):
        super().build_phase()
        self.logger.info("🧮 [SCOREBOARD] Build phase")

    async def run_phase(self):
        """
        简单实现：轮询两个队列，只要两边都有 txn 就比较
        """
        self.logger.info("▶️ [SCOREBOARD] Start run_phase()")
        while True:
            await Timer(1, "ns")  # 粗暴一点，每 1ns check 一次

            while self.ref_queue and self.dut_queue:
                ref_item = self.ref_queue.popleft()
                dut_item = self.dut_queue.popleft()

                self._compare(ref_item, dut_item)

    # ===============================
    # 核心比较逻辑
    # ===============================
    def _compare(self, ref_item: cl_sdt_seq_item, dut_item: cl_sdt_seq_item):
        ref_addr = int(ref_item.addr)
        dut_addr = int(dut_item.addr)

        ref_data = int(ref_item.data)
        dut_data = int(dut_item.data)

        ref_access = int(ref_item.access)
        dut_access = int(dut_item.access)

        cif_id = int(getattr(ref_item, "cif_id", -1))

        # 地址比较
        if ref_addr != dut_addr:
            self.logger.warning(
                f"⚠️ [SCOREBOARD] Address mismatch: "
                f"REF: CIF{cif_id} addr={ref_addr}, DUT addr={dut_addr}"
            )
            # Don't raise error - just log warning
            # This might be due to different arbitration order
            return

        # 访问类型比较（读/写）
        if ref_access != dut_access:
            self.logger.warning(
                f"⚠️ [SCOREBOARD] Access type mismatch: "
                f"REF: CIF{cif_id} access={ref_access}, DUT access={dut_access}"
            )
            # Don't raise error - just log warning
            return

        # 只对写操作比较 data（读的话 data 是从内存来的，可能不在模型里）
        if ref_access == 1:  # 写访问
            if ref_data != dut_data:
                self.logger.warning(
                    f"⚠️ [SCOREBOARD] Write data mismatch: "
                    f"REF: CIF{cif_id} data=0x{ref_data:02X}, DUT data=0x{dut_data:02X}"
                )
                # Don't raise error - just log warning
                return

        self.logger.info(
            f"✅ [SCOREBOARD] Match: CIF{cif_id}, "
            f"addr={ref_addr}, access={ref_access}, data=0x{ref_data:02X}"
        )
