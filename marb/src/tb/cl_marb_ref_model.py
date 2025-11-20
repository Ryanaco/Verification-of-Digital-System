# cl_marb_ref_model.py
import logging
from collections import deque

import pyuvm
from pyuvm import *

from uvc.sdt.src import *                 # cl_sdt_seq_item
from uvc.apb.src import *                 # cl_apb_seq_item
from uvc.apb.src.apb_common import OpType # RD / WR


# ============================================================
# 寄存器地址 / 编码（和 RTL / test 保持一致）
# ============================================================
ARB_MODE_ADDR = 0x00  # control register
C0_PRIO_ADDR  = 0x04  # CIF0 dynamic priority
C1_PRIO_ADDR  = 0x08  # CIF1 dynamic priority
C2_PRIO_ADDR  = 0x0C  # CIF2 dynamic priority

# ctrl 寄存器编码
MODE_STATIC  = 0
MODE_DYNAMIC = 1
ENABLE_OFF   = 0
ENABLE_ON    = 1


class cl_marb_ref_model(uvm_subscriber):
    """
    Memory Arbiter Reference Model  (A5)

    - 继承 uvm_subscriber：
        * 输入：analysis_export
            - 接收 CIF0/1/2 的 SDT request 事务（来自 request_ap）
            - 接收 APB 配置 事务（来自 apb_monitor.ap）
        * 输出：ref_ap（uvm_analysis_port）
            - 把仲裁“获胜”的 golden transaction 推送到 Scoreboard

    - 行为：
        * 维护 ctrl 寄存器：enable / mode (static / dynamic)
        * 维护 DPrio 寄存器：每个 CIF 一个 8bit priority（值越大优先级越高）
        * 为每个 CIF 维护一个 pending request 队列
        * 每次收到新的 CIF request 时，根据当前模式 + priority 决定 winner
        * 将 winner 的 SDT item 通过 ref_ap 发送给 Scoreboard
    """

    def __init__(self, name="cl_marb_ref_model", parent=None):
        super().__init__(name, parent)

        # 输出到 Scoreboard 的 analysis_port
        self.ref_ap = uvm_analysis_port("ref_ap", self)

        # ====== 仲裁配置状态 ======
        self.enable = ENABLE_OFF
        self.mode   = MODE_STATIC

        # dynamic priority 寄存器值：值越大优先级越高
        # index = CIF id (0,1,2)
        self.dprio_vals = [0, 0, 0]

        # ====== pending 请求队列（按 CIF 分开）=====
        # 每个元素是一个 cl_sdt_seq_item
        self.pending = {
            0: deque(),
            1: deque(),
            2: deque(),
        }

        # logger
        self.logger = logging.getLogger("MARB_REF_MODEL")

    # ============================================================
    # 顶层 write()：所有连接到 analysis_export 的数据都从这里进入
    #   - 来自 CIFx request_ap 的 SDT item
    #   - 来自 APB monitor.ap 的 APB item
    # ============================================================
    def write(self, item):
        """
        TLM write() entry point.

        - 如果是 APB 事务：更新寄存器配置（ctrl / dprio）
        - 如果是 SDT 事务：按 CIF id 入队，然后尝试仲裁
        """
        # APB 配置：cl_apb_seq_item
        if isinstance(item, cl_apb_seq_item):
            self._handle_apb(item)
            return

        # SDT 请求：cl_sdt_seq_item
        if isinstance(item, cl_sdt_seq_item):
            self._handle_cif_request(item)
            return

        # 其他类型（意外）：
        self.logger.warning(
            f"[REF MODEL] Received unsupported item type: {type(item)} -> {item}"
        )

    # ============================================================
    # 处理 APB 配置事务
    # ============================================================
    def _handle_apb(self, apb_item: cl_apb_seq_item):
        """
        寄存器配置输入：
        - ctrl register @ 0x00
        - dprio registers @ 0x04, 0x08, 0x0C
        只关心 WR 事务。
        """
        # 只处理写操作
        op = getattr(apb_item, "op", None)
        if op != OpType.WR:
            return

        addr = int(apb_item.addr)
        data = int(apb_item.data)

        if addr == ARB_MODE_ADDR:
            # data[0] = enable
            # data[2:1] = mode
            self.enable = data & 0x1
            self.mode   = (data >> 1) & 0x3

            self.logger.info(
                f"🔧 [REF MODEL] CTRL updated: enable={self.enable}, mode={self.mode}"
            )

        elif addr == C0_PRIO_ADDR:
            self.dprio_vals[0] = data & 0xFF
            self.logger.info(f"🔧 [REF MODEL] dprio[C0] = {self.dprio_vals[0]}")

        elif addr == C1_PRIO_ADDR:
            self.dprio_vals[1] = data & 0xFF
            self.logger.info(f"🔧 [REF MODEL] dprio[C1] = {self.dprio_vals[1]}")

        elif addr == C2_PRIO_ADDR:
            self.dprio_vals[2] = data & 0xFF
            self.logger.info(f"🔧 [REF MODEL] dprio[C2] = {self.dprio_vals[2]}")

        # 配置变化后不立即仲裁，等下一次 request 到来或已有 request 再调用 _maybe_arbitrate()

    # ============================================================
    # 处理 CIF SDT 请求事务
    # ============================================================
    def _handle_cif_request(self, item: cl_sdt_seq_item):
        """
        Stimuli from CIFx request_ap（来自三个 CIF 的 producer uVC）

        需要知道是哪个 CIF 发来的请求：
          - 优先使用 item.cif_id 或 item.client_id（由 monitor 在采样时添加）
          - 如果都没有，则默认 0，并打印 warning
        """
        # 尝试从 item 里推断是哪个 CIF
        if hasattr(item, "cif_id"):
            cid = int(item.cif_id)
        elif hasattr(item, "client_id"):
            cid = int(item.client_id)
        else:
            # 如果 uVC 没有带上 id，就先假设是 CIF0，给个 warning
            cid = 0
            self.logger.warning(
                f"[REF MODEL] SDT item has no cif_id/client_id, "
                f"defaulting to CIF0: item={item}"
            )

        if cid not in (0, 1, 2):
            self.logger.warning(
                f"[REF MODEL] Unexpected CIF id {cid}, ignoring item={item}"
            )
            return

        # 入队
        self.pending[cid].append(item)

        self.logger.debug(
            f"[REF MODEL] Got request from CIF{cid}: "
            f"addr=0x{int(item.addr):02X}, access={int(item.access)}, data=0x{int(item.data):02X}"
        )

        # 每次有新 request 就尝试仲裁一次
        self._maybe_arbitrate()

    # ============================================================
    # 计算当前 priority 顺序
    # ============================================================
    def _current_priority_order(self):
        """
        返回一个 list: 当前优先级顺序中的 CIF id

        - static: 固定 [0,1,2]（CIF0 > CIF1 > CIF2）
        - dynamic: 根据 dprio_vals 排序
            * dprio 值大者优先
            * 相同则 CIF id 小者优先
        """
        if self.mode == MODE_STATIC:
            return [0, 1, 2]

        # dynamic：按 dprio 值从大到小，如果相同，CIF id 小者优先
        ids = [0, 1, 2]
        ids.sort(key=lambda cid: (-self.dprio_vals[cid], cid))
        return ids

    # ============================================================
    # 仲裁核心：根据 current mode + priority 从 pending 中选 winner
    # ============================================================
    def _maybe_arbitrate(self):
        """
        如果 arbiter 使能，并且有 pending 请求，则选择一个 winner，
        构造 ref txn 发给 scoreboard。
        """
        if self.enable != ENABLE_ON:
            # arbiter disabled：在 disable 状态下不产生 ref 输出
            return

        # 计算当前优先级顺序
        order = self._current_priority_order()

        # 按优先级顺序找第一个有 pending 的 CIF
        winner_cid = None
        for cid in order:
            if self.pending[cid]:
                winner_cid = cid
                break

        if winner_cid is None:
            # 没有请求
            return

        # 从该 CIF 的队列中取出最早的请求
        item = self.pending[winner_cid].popleft()

        # 给 item 打上 winner_cid（方便 scoreboard / log）
        setattr(item, "cif_id", winner_cid)

        addr   = int(item.addr)
        data   = int(item.data)
        access = int(item.access)

        self.logger.info(
            f"🏆 [REF MODEL] Winner: CIF{winner_cid} "
            f"(addr={addr}, access={access}, data=0x{data:02X})"
        )

        # 把“golden txn”送给 Scoreboard
        self.ref_ap.write(item)

    # ============================================================
    # 可选：final_phase() 时报告是否还有 pending
    # ============================================================
    def final_phase(self):
        super().final_phase()
        total_pending = sum(len(q) for q in self.pending.values())
        if total_pending > 0:
            self.logger.warning(
                f"[REF MODEL] final_phase: {total_pending} pending requests left in queues"
            )
