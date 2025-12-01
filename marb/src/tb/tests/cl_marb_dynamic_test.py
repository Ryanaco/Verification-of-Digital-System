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
from uvc.apb.src.apb_common import OpType
from uvc.sdt.src import *          # sdt_common, cl_sdt_interface, cl_sdt_seq_item, ...
from uvc.sdt.src.cl_sdt_config import cl_sdt_config

from cl_marb_tb_config import cl_marb_tb_config
from cl_marb_tb_env import cl_marb_tb_env
from cl_marb_tb_base_test import cl_marb_tb_base_test

seq_logger = logging.getLogger("MARB_DYNAMIC_SEQ")
_LOG_LEVELS = ["DEBUG", "CRITICAL", "ERROR", "WARNING", "INFO", "NOTSET", "NullHandler"]


# ============================================================
# 寄存器地址 / 常量
# ============================================================
ARB_MODE_ADDR       = 0x00  # control register 地址
ARB_DPRIO_ADDR      = 0x04  # dynamic priority register 地址 (包含 C0, C1, C2)
                             # [7:0]=dprio[0]=C0, [15:8]=dprio[1]=C1, [23:16]=dprio[2]=C2

# 控制寄存器编码：
# bit0: enable
# bits[2:1]: mode (0 = static, 1 = dynamic)
MODE_STATIC  = 0
MODE_DYNAMIC = 1

ENABLE_OFF = 0
ENABLE_ON  = 1


# ============================================================
# APB sequence：配置 Dynamic Priority 模式 + 随机优先级
#   - 先 disable arbiter
#   - 写 dynamic priority
#   - 等待 sorter 完成（>= 6 cycles）
#   - 再 enable arbiter
# ============================================================
class cl_marb_dynamic_apb_cfg_seq(uvm_sequence):

    def __init__(self, name="cl_marb_dynamic_apb_cfg_seq",
                 c0_prio=0, c1_prio=0, c2_prio=0):
        super().__init__(name)
        self.c0_prio = c0_prio
        self.c1_prio = c1_prio
        self.c2_prio = c2_prio

    async def body(self):
        seq_logger.info(
            f"⚙️ [APB_CFG] Configure arbiter as DYNAMIC mode "
            f"with priorities C0={self.c0_prio}, C1={self.c1_prio}, C2={self.c2_prio}"
        )

        try:
            # -------------------------
            # 1) Disable arbiter, set mode = DYNAMIC
            # -------------------------
            item = cl_apb_seq_item.create("ctrl_disable_dynamic")
            item.addr = ARB_MODE_ADDR
            # mode = 1 (dynamic), enable = 0
            item.data = (MODE_DYNAMIC << 1) | ENABLE_OFF
            item.op   = OpType.WR
            item.strb = 0xF
            await self.start_item(item)
            await self.finish_item(item)
            seq_logger.info("  - CTRL: enable=0, mode=DYNAMIC (disable arbiter for dprio update)")

            # -------------------------
            # 2) 写三个 CIF 的 dynamic priority
            #    RTL设计：一个32bit寄存器包含4个client的priority
            #    文档说明：值越大优先级越高
            # -------------------------
            # 组合三个priority为单一32bit数据
            combined_dprio = (self.c0_prio & 0xFF) | ((self.c1_prio & 0xFF) << 8) | ((self.c2_prio & 0xFF) << 16)
            
            item = cl_apb_seq_item.create("dprio_combined_item")
            item.addr = ARB_DPRIO_ADDR
            item.data = combined_dprio
            item.op   = OpType.WR
            item.strb = 0xF  # Write all 4 bytes
            await self.start_item(item)
            await self.finish_item(item)
            seq_logger.info(
                f"  - Set dynamic priorities (combined) @0x{ARB_DPRIO_ADDR:08X} = 0x{combined_dprio:08X}"
                f" (C0={self.c0_prio:02X}, C1={self.c1_prio:02X}, C2={self.c2_prio:02X})"
            )

            # -------------------------
            # 3) 等待排序完成
            #    设计文档说内部 sorter 需要 6 cycles
            #    我们这里等待足够的时间确保安全
            # -------------------------
            seq_logger.info("  - Waiting for internal sorter to finish (waiting 200 ns)...")
            await Timer(200, units="ns")
            seq_logger.info("  - Wait completed, proceeding to enable")

            # -------------------------
            # 4) Re-enable arbiter, mode=DYNAMIC
            # -------------------------
            seq_logger.info("  - Now starting Re-enable write item...")
            item = cl_apb_seq_item.create("ctrl_enable_dynamic")
            item.addr = ARB_MODE_ADDR
            item.data = (MODE_DYNAMIC << 1) | ENABLE_ON   # mode=1, enable=1 -> 0x03
            item.op   = OpType.WR
            item.strb = 0xF
            seq_logger.info(f"  - Re-enable item: addr=0x{item.addr:02X}, data=0x{item.data:08X}, op={item.op}, strb=0x{item.strb:X}")
            await self.start_item(item)
            seq_logger.info("  - start_item done, now finish_item...")
            await self.finish_item(item)
            seq_logger.info("  - finish_item done")
            seq_logger.info("  - CTRL: enable=1, mode=DYNAMIC (arbiter enabled with new priorities)")
            
            # 额外等待确保APB写入完全完成
            await Timer(100, units="ns")

            seq_logger.info("✅ [APB_CFG] Dynamic arbiter config done")
            
        except Exception as e:
            seq_logger.error(f"❌ [APB_CFG] Exception during APB config: {e}")
            seq_logger.error(f"   Exception type: {type(e)}")
            import traceback
            seq_logger.error(f"   Traceback: {traceback.format_exc()}")
            raise


# ============================================================
# SDT client sequence：
#   发送随机读/写请求，用来制造争用
# ============================================================
class cl_marb_dynamic_cif_seq(uvm_sequence):

    def __init__(self,
                 name="cl_marb_dynamic_cif_seq",
                 client_id=0,
                 num_reqs=10,
                 addr_low=0x00,
                 addr_high=0x3F):
        super().__init__(name)
        self.client_id = client_id
        self.num_reqs = num_reqs
        self.addr_low = addr_low
        self.addr_high = addr_high

    async def body(self):
        seq_logger.info(
            f"🧪 [CIF{self.client_id}] Dynamic traffic: {self.num_reqs} random requests"
        )

        for i in range(self.num_reqs):
            addr = randint(self.addr_low, self.addr_high)
            data = randint(0, 0xFF)
            # 0 = READ, 1 = WRITE（简单 50/50）
            access = randint(0, 1)

            item = cl_sdt_seq_item.create(f"cif{self.client_id}_item{i}")
            item.addr   = addr
            item.data   = data
            item.access = access

            await self.start_item(item)
            await self.finish_item(item)

            op_str = "WRITE" if access == 1 else "READ "
            seq_logger.info(
                f"  - CIF{self.client_id} {op_str} addr=0x{addr:02X}, data=0x{data:02X}"
            )

        seq_logger.info(f"✅ [CIF{self.client_id}] Dynamic traffic sequence done")


# ============================================================
# Virtual Sequence：
#   - 随机生成 dynamic priorities
#   - 调 APB sequence 配好 DYN 模式
#   - 三个 CIF 并发发请求
# ============================================================
class cl_marb_dynamic_vseq(uvm_sequence):

    def __init__(self, name="cl_marb_dynamic_vseq"):
        super().__init__(name)

    async def body(self):
        seq_logger.info("🎬 [VSEQ] Dynamic priority virtual sequence starting")

        # virtual_sequencer 在 env.connect_phase 里已经挂好：
        #   - self.sequencer.apb_seqr
        #   - self.sequencer.cif_seqrs = [cif0_seqr, cif1_seqr, cif2_seqr]
        vseqr = self.sequencer
        apb_seqr = vseqr.apb_seqr
        cif_seqrs = vseqr.cif_seqrs

        # -------------------------
        # 1) 随机生成三个 CIF 的 priority
        #    文档：值越大优先级越高
        # -------------------------
        c0_prio = randint(0, 255)
        c1_prio = randint(0, 255)
        c2_prio = randint(0, 255)

        seq_logger.info(
            f"🧮 [VSEQ] Random dynamic priorities: "
            f"C0={c0_prio}, C1={c1_prio}, C2={c2_prio}"
        )

        # -------------------------
        # 2) 跑 APB 配置 sequence（disable -> 写 dprio -> wait -> enable）
        # -------------------------
        apb_cfg_seq = cl_marb_dynamic_apb_cfg_seq(
            "apb_dynamic_cfg_seq",
            c0_prio=c0_prio,
            c1_prio=c1_prio,
            c2_prio=c2_prio
        )

        seq_logger.info("⚙️ [VSEQ] Starting APB dynamic config sequence...")
        await apb_cfg_seq.start(apb_seqr)
        seq_logger.info("✅ [VSEQ] APB dynamic config finished")

        # -------------------------
        # 3) 创建三个 CIF 的 random traffic sequence
        #    每个 CIF 随机 5~15 个请求
        # -------------------------
        cif_seqs = []
        for cid in range(3):
            num_reqs = randint(5, 15)
            seq = cl_marb_dynamic_cif_seq(
                name=f"cif{cid}_dyn_seq",
                client_id=cid,
                num_reqs=num_reqs,
                addr_low=0x10,   # 随便选一段地址区
                addr_high=0x3F
            )
            cif_seqs.append(seq)
            seq_logger.info(f"📌 [VSEQ] CIF{cid} will send {num_reqs} requests")

        # -------------------------
        # 4) 并发启动 CIF0/1/2 sequence
        # -------------------------
        seq_logger.info("🚀 [VSEQ] Starting CIF0/1/2 dynamic sequences in parallel...")

        tasks = []
        for cid, seq in enumerate(cif_seqs):
            tasks.append(
                cocotb.start_soon(
                    seq.start(cif_seqrs[cid])
                )
            )

        # 等待所有 CIF sequence 完成
        for t in tasks:
            await t

        seq_logger.info("📤 [VSEQ] All CIF dynamic sequences completed")
        seq_logger.info("🏁 [VSEQ] Dynamic priority virtual sequence done")


# ============================================================
# Dynamic 测试本体：继承 Base Test
# ============================================================
@pyuvm.test()
class cl_marb_tb_dynamic_test(cl_marb_tb_base_test):
    """
    A4.2 Dynamic Priority Random Traffic Test

    - 继承 A3 base env
    - 用 APB 把仲裁器设置为 DYNAMIC 模式
    - 随机生成 C0/C1/C2 的 dynamic priority
    - 三个 CIF 发随机读/写请求，制造争用
    - 必须在 disable 状态下修改 dynamic priority
    - 写完 priority 后等待 sorter 完成，再 enable
    - 通过 REF Model + Scoreboard 自动检查仲裁行为
    """

    def __init__(self, name="cl_marb_tb_dynamic_test", parent=None):
        super().__init__(name, parent)

    async def run_phase(self):
        self.raise_objection()
        self.logger.info("▶️ [RUN] Starting MARB DYNAMIC random test run_phase()")

        # 启动时钟 + 复位（复用 base_test 的 helper）
        await self.start_clock()
        await self.trigger_reset()

        # 启动 dynamic virtual sequence
        vseq = cl_marb_dynamic_vseq("dynamic_vseq")
        self.logger.info("🎯 Starting dynamic virtual sequence on env.virtual_sequencer")
        await vseq.start(self.marb_tb_env.virtual_sequencer)

        self.logger.info("🏁 DYNAMIC random test completed")
        self.drop_objection()
