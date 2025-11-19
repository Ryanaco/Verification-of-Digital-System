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
from uvc.apb.src.apb_common import OpType  # ✅ 导入 OpType
from uvc.sdt.src import *          # sdt_common, cl_sdt_interface, cl_sdt_seq_item, ...
from uvc.sdt.src.cl_sdt_config import cl_sdt_config

from cl_marb_tb_config import cl_marb_tb_config
from cl_marb_tb_env import cl_marb_tb_env
from cl_marb_tb_base_test import cl_marb_tb_base_test

seq_logger = logging.getLogger("MARB_STATIC_SEQ")
_LOG_LEVELS = ["DEBUG", "CRITICAL", "ERROR", "WARNING", "INFO", "NOTSET", "NullHandler"]


# ============================================================
# 一些寄存器地址 / 字段值常量 —— 按课程文档自己修改
# ============================================================

# TODO: 根据你的 mem_arb 寄存器定义修改这些地址
ARB_MODE_ADDR   = 0x00  # 仲裁模式配置寄存器地址
C0_PRIO_ADDR    = 0x04  # client0 优先级寄存器地址
C1_PRIO_ADDR    = 0x08  # client1 优先级寄存器地址
C2_PRIO_ADDR    = 0x0C  # client2 优先级寄存器地址

# TODO: 根据文档定义 static 模式的编码，比如 0: static, 1: round-robin
ARB_MODE_STATIC = 0x0

# 优先级数值：数值越小优先级越高（或反过来，看你设计）
C0_PRIORITY = 0  # 最高
C1_PRIORITY = 1
C2_PRIORITY = 2


# ============================================================
# APB 配置 sequence：配置仲裁模式 + client 优先级
# ============================================================
class cl_marb_static_apb_cfg_seq(uvm_sequence):

    def __init__(self, name="cl_marb_static_apb_cfg_seq"):
        super().__init__(name)

    async def body(self):
        # 用全局的 Python logger，而不是 self.logger
        seq_logger.info("⚙️ [APB_CFG] Configure arbiter as STATIC mode + priorities")

        # ------------------------------------------------------------------
        # 下面假设有一个 cl_apb_seq_item，字段：addr, data, op, strb
        # 如果你实际 UVC 不同，在这里改类名 & 字段名即可
        # ------------------------------------------------------------------

        # 写仲裁模式寄存器
        item = cl_apb_seq_item.create("arb_mode_item")
        item.addr  = ARB_MODE_ADDR
        item.data  = (ARB_MODE_STATIC << 1) | 0x1     # <-- enable + mode
        item.op    = OpType.WR  # ✅ 使用 OpType.WR 而不是 write=1
        item.strb  = 0xF
        await self.start_item(item)
        await self.finish_item(item)
        seq_logger.info(f"  - Set ARB_MODE = STATIC + ENABLE")

        # C0 priority
        item = cl_apb_seq_item.create("c0_prio_item")
        item.addr  = C0_PRIO_ADDR
        item.data  = C0_PRIORITY
        item.op    = OpType.WR
        item.strb  = 0xF
        await self.start_item(item)
        await self.finish_item(item)
        seq_logger.info(f"  - Set C0 priority @0x{C0_PRIO_ADDR:08X} = {C0_PRIORITY}")

        # C1 priority
        item = cl_apb_seq_item.create("c1_prio_item")
        item.addr  = C1_PRIO_ADDR
        item.data  = C1_PRIORITY
        item.op    = OpType.WR
        item.strb  = 0xF
        await self.start_item(item)
        await self.finish_item(item)
        seq_logger.info(f"  - Set C1 priority @0x{C1_PRIO_ADDR:08X} = {C1_PRIORITY}")

        # C2 priority
        item = cl_apb_seq_item.create("c2_prio_item")
        item.addr  = C2_PRIO_ADDR
        item.data  = C2_PRIORITY
        item.op    = OpType.WR
        item.strb  = 0xF
        await self.start_item(item)
        await self.finish_item(item)
        seq_logger.info(f"  - Set C2 priority @0x{C2_PRIO_ADDR:08X} = {C2_PRIORITY}")

        seq_logger.info("✅ [APB_CFG] Arbiter static config done")


# ============================================================
# 简单的 SDT client sequence：
#   在固定地址做若干写操作，用来制造争用
# ============================================================
class cl_marb_static_cif_seq(uvm_sequence):

    def __init__(self, name="cl_marb_static_cif_seq", client_id=0, base_addr=0x10):
        super().__init__(name)
        self.client_id = client_id
        self.base_addr = base_addr

    async def body(self):
        seq_logger.info(f"🧪 [CIF{self.client_id}] Static traffic sequence start")

        # 这里简单发 4 个写请求到同一片地址区域
        for i in range(4):
            addr = self.base_addr + i

            # 假设 SDT seq_item 名叫 cl_sdt_seq_item
            item = cl_sdt_seq_item.create(f"cif{self.client_id}_item{i}")
            item.addr    = addr
            item.data    = (self.client_id << 4) + i  # ✅ 改成 data 而不是 wr_data
            item.access  = 1  # ✅ 1 = WRITE，0 = READ

            await self.start_item(item)
            await self.finish_item(item)

            seq_logger.info(
                f"  - CIF{self.client_id} WRITE addr=0x{addr:02X}, data=0x{item.data:02X}"
            )

        seq_logger.info(f"✅ [CIF{self.client_id}] Static traffic sequence done")


# ============================================================
# Static 测试本体：继承 Base Test
# ============================================================
@pyuvm.test()
class cl_marb_tb_static_test(cl_marb_tb_base_test):
    """
    A4 Static Arbiter Test

    - 继承 A3 base env
    - 用 APB 把仲裁器设置为 STATIC 模式
    - 配置 C0 > C1 > C2 优先级
    - 三个 CIF 在同一段地址发写请求，制造争用
    - 通过波形 / log 观察最高优先级是否总是先被服务
    """

    def __init__(self, name="cl_marb_tb_static_test", parent=None):
        super().__init__(name, parent)

    # build_phase / connect_phase 直接复用 base_test 的
    # 如果需要也可以在这里 override，但现在没必要

    async def run_phase(self):
        self.raise_objection()
        self.logger.info("▶️ [RUN] Starting MARB STATIC test run_phase()")

        # 启动时钟 + 复位
        await self.start_clock()
        await self.trigger_reset()

        # -------------------------
        # 1) APB 配置 static 模式
        # -------------------------
        apb_cfg_seq = cl_marb_static_apb_cfg_seq("apb_cfg_seq")
        await apb_cfg_seq.start(self.marb_tb_env.apb_agent.sequencer)

        self.logger.info("⚙️ APB 配置完成，进入 static 仲裁模式")

        # ✅ 等待额外时间确保 driver 已准备好
        await Timer(100, units="ns")
        self.logger.info("✅ 等待 driver 准备完毕")

        # -------------------------
        # 2) 启动 CIF0/1/2 写请求
        # -------------------------
        # ❌ 原来是 cl_static_cif_seq —— 不存在
        # ✅ 改成你上面定义的 cl_marb_static_cif_seq
        cif0_seq = cl_marb_static_cif_seq("c0_seq", client_id=0, base_addr=0x10)
        cif1_seq = cl_marb_static_cif_seq("c1_seq", client_id=1, base_addr=0x10)
        cif2_seq = cl_marb_static_cif_seq("c2_seq", client_id=2, base_addr=0x10)

        self.logger.info("🚀 启动 CIF0/1/2 sequence ...")
        self.logger.info(f"🔍 CIF0 sequencer: {self.marb_tb_env.cif0_agent.sequencer}")
        self.logger.info(f"🔍 CIF0 agent has driver: {hasattr(self.marb_tb_env.cif0_agent, 'driver')}")
        
        # 现在先顺序跑，能工作再考虑并行
        self.logger.info("▶️ Starting CIF0 sequence...")
        await cif0_seq.start(self.marb_tb_env.cif0_agent.sequencer)
        self.logger.info("✅ CIF0 sequence finished")
        
        self.logger.info("▶️ Starting CIF1 sequence...")
        await cif1_seq.start(self.marb_tb_env.cif1_agent.sequencer)
        self.logger.info("✅ CIF1 sequence finished")
        
        self.logger.info("▶️ Starting CIF2 sequence...")
        await cif2_seq.start(self.marb_tb_env.cif2_agent.sequencer)
        self.logger.info("✅ CIF2 sequence finished")

        self.logger.info("📤 全部 CIF sequence 执行完毕")

        self.drop_objection()
        self.logger.info("🏁 STATIC TEST 完成")
