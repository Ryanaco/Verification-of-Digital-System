import os
import warnings
from random import randint

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer
import logging
import vsc
import pyuvm
from pyuvm import *

# -------------------------------------------------------
# Import UVC components
# -------------------------------------------------------
from uvc.apb.src import *          # apb_common, cl_apb_interface, cl_apb_seq_item, ...
from uvc.apb.src.apb_common import OpType  # APB op type
from uvc.sdt.src import *          # sdt_common, cl_sdt_interface, cl_sdt_seq_item, ...
from uvc.sdt.src.cl_sdt_config import cl_sdt_config

from cl_marb_tb_config import cl_marb_tb_config
from cl_marb_tb_env import cl_marb_tb_env
from cl_marb_tb_base_test import cl_marb_tb_base_test

seq_logger = logging.getLogger("MARB_STATIC_SEQ")
_LOG_LEVELS = ["DEBUG", "CRITICAL", "ERROR", "WARNING", "INFO", "NOTSET", "NullHandler"]


# ============================================================
# APB 地址 / 寄存器字段定义（根据文档）
# ============================================================

# 控制寄存器地址：enable + mode
ARB_CTRL_ADDR   = 0x00  # Control register (enable + mode)

# Dynamic priority 寄存器起始地址（一个 32bit 寄存器，8bit × 4 CIF）
DPRIO_ADDR      = 0x04  # DPrio base address (cif0[7:0], cif1[15:8], cif2[23:16])

# mode 定义：0 = static，1 = dynamic
ARB_MODE_STATIC = 0x0

# static 模式下默认优先级：CIF0 > CIF1 > CIF2
# （RTL 里 static priority 是固定顺序；这里写 DPrio 只是为了更清晰）
C0_PRIORITY = 2  # 优先级值越大优先级越高（根据文档 DPrio 定义）
C1_PRIORITY = 1
C2_PRIORITY = 0


# ============================================================
# APB 配置 sequence：配置仲裁模式 + client 优先级
# ============================================================
class cl_marb_static_apb_cfg_seq(uvm_sequence):

    def __init__(self, name="cl_marb_static_apb_cfg_seq"):
        super().__init__(name)

    async def body(self):
        seq_logger.info("⚙️ [APB_CFG] Configure arbiter as STATIC mode + priorities")

        # ------------------------------------------------------
        # 1) 写 Control 寄存器：enable=1, mode=STATIC(0)
        #    control[0] = enable
        #    control[2:1] = mode
        # ------------------------------------------------------
        ctrl_value = (ARB_MODE_STATIC << 1) | 0x1

        item = cl_apb_seq_item.create("arb_ctrl_item")
        item.addr  = ARB_CTRL_ADDR
        item.data  = ctrl_value
        item.op    = OpType.WR
        item.strb  = 0xF
        await self.start_item(item)
        await self.finish_item(item)
        seq_logger.info(f"  - Set CTRL @0x{ARB_CTRL_ADDR:08X} = 0x{ctrl_value:08X} "
                        f"(mode=STATIC, enable=1)")

        # ------------------------------------------------------
        # 2) 写 DPrio 寄存器（可选，对 static 模式行为无影响，
        #    只是让寄存器内容更“好看”）
        #    DPrio[ 7: 0] = CIF0
        #          [15: 8] = CIF1
        #          [23:16] = CIF2
        # ------------------------------------------------------
        dprio_value = (
            (C2_PRIORITY & 0xFF) << 16 |
            (C1_PRIORITY & 0xFF) << 8  |
            (C0_PRIORITY & 0xFF)
        )

        item = cl_apb_seq_item.create("dprio_item")
        item.addr  = DPRIO_ADDR
        item.data  = dprio_value
        item.op    = OpType.WR
        item.strb  = 0xF
        await self.start_item(item)
        await self.finish_item(item)
        seq_logger.info(
            f"  - Set DPRIO @0x{DPRIO_ADDR:08X} = 0x{dprio_value:08X} "
            f"(c0={C0_PRIORITY}, c1={C1_PRIORITY}, c2={C2_PRIORITY})"
        )

        seq_logger.info("✅ [APB_CFG] Arbiter static config done")


# ============================================================
# SDT client sequence（Producer）：随机流量 + 地址重叠制造争用
# ============================================================
class cl_marb_static_cif_seq(uvm_sequence):
    """
    针对单个 CIF 的随机 traffic sequence：
      - 在一个小地址窗口内随机读/写
      - 随机事务数量
      - 连续发送，制造与其他 CIF 的竞争
    """

    def __init__(self,
                 name="cl_marb_static_cif_seq",
                 client_id=0,
                 base_addr=0x10,
                 num_min=5,
                 num_max=15):
        super().__init__(name)
        self.client_id = client_id
        self.base_addr = base_addr
        self.num_min   = num_min
        self.num_max   = num_max

    async def body(self):
        num_txn = randint(self.num_min, self.num_max)
        seq_logger.info(
            f"🧪 [CIF{self.client_id}] Static traffic start, num_txn={num_txn}, "
            f"base_addr=0x{self.base_addr:02X}"
        )

        for i in range(num_txn):
            # 在 base_addr ~ base_addr+0x0F 范围随机访问，
            # 这样不同 CIF 会非常容易“撞车”
            addr = self.base_addr + randint(0, 0x0F)

            # 0: READ, 1: WRITE
            access = randint(0, 1)
            data   = randint(0, 0xFF)

            item = cl_sdt_seq_item.create(f"cif{self.client_id}_item{i}")
            item.addr   = addr
            item.data   = data
            item.access = access  # 1 = WRITE, 0 = READ

            await self.start_item(item)
            await self.finish_item(item)

            if access == 1:
                seq_logger.info(
                    f"  - CIF{self.client_id} WRITE addr=0x{addr:02X}, data=0x{data:02X}"
                )
            else:
                seq_logger.info(
                    f"  - CIF{self.client_id} READ  addr=0x{addr:02X}"
                )

            # 在事务之间插一点随机空闲时间，让不同 CIF 更容易错位/重叠
            await Timer(randint(0, 10), units="ns")

        seq_logger.info(f"✅ [CIF{self.client_id}] Static traffic sequence done")


# ============================================================
# Virtual Sequence：统一控制 APB + 三个 CIF 的随机 traffic
# ============================================================
class cl_marb_static_vseq(uvm_sequence):
    """
    STATIC 模式并发随机 traffic 的 virtual sequence
    """

    def __init__(self, name="cl_marb_static_vseq"):
        super().__init__(name)

    async def body(self):
        # pyuvm 中 sequencer 的访问方式是 self.sequencer
        vseqr = self.sequencer
        seq_logger.info("🎬 [VSEQ] Static random traffic virtual sequence start")

        # 1) APB 配置 static 模式
        apb_cfg_seq = cl_marb_static_apb_cfg_seq("apb_cfg_seq")
        await apb_cfg_seq.start(vseqr.apb_seqr)
        seq_logger.info("⚙️ [VSEQ] APB static config completed")

        # 2) 随机冲突地址窗口
        base_addr = randint(0x10, 0x40)
        seq_logger.info(
            f"📍 [VSEQ] Conflict address window base = 0x{base_addr:02X}"
        )

        cif0_seq = cl_marb_static_cif_seq("c0_seq", client_id=0, base_addr=base_addr)
        cif1_seq = cl_marb_static_cif_seq("c1_seq", client_id=1, base_addr=base_addr)
        cif2_seq = cl_marb_static_cif_seq("c2_seq", client_id=2, base_addr=base_addr)

        seq_logger.info("🚀 [VSEQ] Launch CIF0/1/2 sequences in parallel ...")

        # 并发执行
        t0 = cocotb.start_soon(cif0_seq.start(vseqr.cif_seqrs[0]))
        t1 = cocotb.start_soon(cif1_seq.start(vseqr.cif_seqrs[1]))
        t2 = cocotb.start_soon(cif2_seq.start(vseqr.cif_seqrs[2]))

        await t0
        await t1
        await t2

        seq_logger.info("📤 [VSEQ] All CIF sequences completed")
        seq_logger.info("🏁 [VSEQ] Static random traffic virtual sequence done")


# ============================================================
# Static 测试本体：继承 Base Test
# ============================================================
@pyuvm.test()
class cl_marb_tb_static_test(cl_marb_tb_base_test):
    """
    A4.1 Random traffic test case with STATIC priority

    - 复用 A3 base env(APB + 3x CIF + 1x MIF + virtual sequencer)
    - 用 APB 把仲裁器设置为 STATIC 模式(mode=0, enable=1)
    - 通过 virtual sequence 并发发起 CIF0/1/2 的随机 traffic
    - 地址窗口重叠 => 制造争用
    - 通过波形 / log 观察：
        * 高优先级 CIF0 应当"更容易"被服务
        * 不会出现多个 CIF 同时 ack
    """

    def __init__(self, name="cl_marb_tb_static_test", parent=None):
        super().__init__(name, parent)

    async def run_phase(self):
        self.raise_objection()
        self.logger.info("▶️ [RUN] Starting MARB STATIC random test run_phase()")

        # 1) 启动时钟 + 复位（复用 base_test 的实现）
        await self.start_clock()
        await self.trigger_reset()

        # 2) 启动 static virtual sequence
        vseq = cl_marb_static_vseq("static_vseq")

        # 这里使用 env 里的 virtual_sequencer
        self.logger.info("🎯 Starting static virtual sequence on env.virtual_sequencer")
        await vseq.start(self.marb_tb_env.virtual_sequencer)

        # 3) 等待一点时间，让最后几个 handshake / ack 走完，美化波形
        await Timer(100, units="ns")

        self.logger.info("🏁 STATIC random test completed")
        self.drop_objection()

