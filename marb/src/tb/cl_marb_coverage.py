# cl_marb_coverage.py
#
# MARB coverage collector
#
# - 作为 uvm_subscriber，连到 MIF monitor 的 ap
# - 使用 PyVSC 做功能覆盖，并通过 UCIS 导出
#
# 需求对应：
#   1) 继承 uvm_subscriber，连接到 MIF monitor
#   2) 覆盖点：同一地址的 WR 后跟 RD（支持 back-to-back 和非连续）
#   3) burst 覆盖：连续地址的最长长度、起始地址 x 长度 的交叉
#   4) 在 write() 中对每个事务进行 sample
#

from pyuvm import *
import vsc

# 从 SDT UVC 里拿 transaction 和访问类型
from uvc.sdt.src.cl_sdt_seq_item import cl_sdt_seq_item
from uvc.sdt.src.sdt_common import AccessType


# ---------------------------------------------------------
#  Covergroup 定义
# ---------------------------------------------------------

@vsc.covergroup
class WrRdSameAddrB2BCg(object):
    """
    覆盖：写之后紧跟着读同地址（Back-to-back）
    - coverpoint: address
    - 每个地址一个 bin（使用 bin_array 自动展开）
    """
    def __init__(self, addr_getter, addr_max):
        # addr_getter: callable -> 当前 sample 的地址
        self.cp_addr = vsc.coverpoint(
            addr_getter,
            bins={
                "addr": vsc.bin_array([], [0, addr_max])
            }
        )


@vsc.covergroup
class WrRdSameAddrNonConsecCg(object):
    """
    覆盖：写之后（允许中间插入其它地址访问）再读同地址（Non-consecutive）
    - coverpoint: address
    """
    def __init__(self, addr_getter, addr_max):
        self.cp_addr = vsc.coverpoint(
            addr_getter,
            bins={
                "addr": vsc.bin_array([], [0, addr_max])
            }
        )


@vsc.covergroup
class BurstCg(object):
    """
    覆盖：burst 检测
    - coverpoint: burst_start_addr
    - coverpoint: burst_len
    - cross: start x len
    """
    def __init__(self, start_addr_getter, length_getter, addr_max):
        # 起始地址：0 .. addr_max
        self.cp_start = vsc.coverpoint(
            start_addr_getter,
            bins={
                "start": vsc.bin_array([], [0, addr_max])
            }
        )

        # burst 长度：至少 1，最大可以到地址空间大小
        max_len = addr_max + 1
        self.cp_len = vsc.coverpoint(
            length_getter,
            bins={
                # 这里用自动 bins 覆盖 1..max_len
                "len": vsc.bin_array([], [1, max_len])
            }
        )

        # 交叉覆盖：起始地址 x 长度
        self.start_x_len = vsc.cross([self.cp_start, self.cp_len])


# ---------------------------------------------------------
#  纯 Python 覆盖模型：维护状态 + 调用 covergroup.sample()
# ---------------------------------------------------------

class MarbCoverageModel:
    """
    内部状态机，基于 MIF monitor 送来的 cl_sdt_seq_item 做覆盖采样
    """

    def __init__(self, addr_width=8):
        self.addr_width = addr_width
        self.addr_max = (1 << addr_width) - 1

        # ---- 状态：WR-RD same address 覆盖 ----
        # Back-to-back：记住上一笔访问
        self.last_access_addr = None
        self.last_access_is_wr = False

        # Non-consecutive：记录某个地址是否曾经写过
        # （简单用 set 实现，每看到 WR 就加入，看到 RD 同地址就 hit）
        self.written_addr_set = set()

        # ---- 状态：burst 覆盖 ----
        self.burst_active = False
        self.burst_start_addr = 0
        self.burst_len = 0
        self.burst_prev_addr = None

        # ---- 给 covergroup 调用的“当前样本变量” ----
        self.curr_addr_for_wr_rd = 0
        self.curr_burst_start = 0
        self.curr_burst_len = 0

        # ---- 实例化 covergroups ----
        self.wr_rd_b2b_cg = WrRdSameAddrB2BCg(
            lambda: self.curr_addr_for_wr_rd,
            self.addr_max
        )

        self.wr_rd_nonconsec_cg = WrRdSameAddrNonConsecCg(
            lambda: self.curr_addr_for_wr_rd,
            self.addr_max
        )

        self.burst_cg = BurstCg(
            lambda: self.curr_burst_start,
            lambda: self.curr_burst_len,
            self.addr_max
        )

    # -------------------------------
    #  对外接口：处理一个 transaction
    # -------------------------------
    def sample_transaction(self, item: cl_sdt_seq_item):
        """
        对一笔 MIF 的 cl_sdt_seq_item 做所有覆盖采样
        """
        # 只关心有地址的访问
        if item.addr is None:
            return

        addr = int(item.addr)
        access = int(item.access)

        is_wr = (access == int(AccessType.WR))
        is_rd = (access == int(AccessType.RD))

        # 1) WR-RD same address 覆盖
        self._sample_wr_rd_same_addr(addr, is_wr, is_rd)

        # 2) Burst 覆盖（只对 write 检测连续地址）
        self._update_and_sample_burst(addr, is_wr, is_rd)

    # -------------------------------
    #  1) 写后读同地址覆盖
    # -------------------------------
    def _sample_wr_rd_same_addr(self, addr: int, is_wr: bool, is_rd: bool):
        # ----- Back-to-back：上一笔是 WR，同一地址，现在是 RD -----
        if (
            self.last_access_is_wr
            and is_rd
            and self.last_access_addr is not None
            and addr == self.last_access_addr
        ):
            # 命中 back-to-back WR->RD same addr
            self.curr_addr_for_wr_rd = addr
            self.wr_rd_b2b_cg.sample()

        # ----- Non-consecutive：某地址曾经 WR，后来 RD 同地址 -----
        if is_wr:
            self.written_addr_set.add(addr)

        if is_rd and addr in self.written_addr_set:
            self.curr_addr_for_wr_rd = addr
            self.wr_rd_nonconsec_cg.sample()
            # 是否清除由你决定，这里选择保留（一个地址可以多次 hit）

        # 更新“上一笔访问”的状态
        if is_wr or is_rd:
            self.last_access_addr = addr
            self.last_access_is_wr = is_wr
        else:
            # 其他类型访问（如果有的话）不重置 last_access
            pass

    # -------------------------------
    #  2) Burst 覆盖（顺序地址）
    # -------------------------------
    def _update_and_sample_burst(self, addr: int, is_wr: bool, is_rd: bool):
        # 只有 WR 参与 burst 检测
        if not is_wr:
            # 如果之前有正在进行的 burst，则在非写访问时“结束并采样”
            if self.burst_active and self.burst_len > 0:
                self._sample_current_burst()
            return

        # 到这里：当前是一个 write 事务
        if not self.burst_active:
            # 启动新的 burst
            self.burst_active = True
            self.burst_start_addr = addr
            self.burst_prev_addr = addr
            self.burst_len = 1
            return

        # 已经在 burst 中：检查是否是连续地址
        expected_next = (self.burst_prev_addr + 1) & self.addr_max
        if addr == expected_next:
            # 仍在同一个 burst 中
            self.burst_len += 1
            self.burst_prev_addr = addr
        else:
            # burst 断开，先采样之前的 burst，然后开启新的
            self._sample_current_burst()
            self.burst_active = True
            self.burst_start_addr = addr
            self.burst_prev_addr = addr
            self.burst_len = 1

    def _sample_current_burst(self):
        """
        将当前 burst_start_addr / burst_len 送入 covergroup 做采样
        """
        if self.burst_len <= 0:
            return

        self.curr_burst_start = int(self.burst_start_addr)
        self.curr_burst_len = int(self.burst_len)
        self.burst_cg.sample()

        # 重置状态，等待下一个 burst
        self.burst_active = False
        self.burst_len = 0
        self.burst_prev_addr = None


# ---------------------------------------------------------
#  覆盖收集器：UVM subscriber
# ---------------------------------------------------------

class cl_marb_coverage_collector(uvm_subscriber):
    """
    - 继承自 uvm_subscriber
    - 通过 analysis_export 接收 MIF monitor 的 cl_sdt_seq_item
    - 内部持有 MarbCoverageModel，在 write() 里 sample
    """

    def __init__(self, name, parent):
        super().__init__(name, parent)

        # 如果以后想从 cfg 里拿地址宽度，可以在 build_phase 里做
        self.addr_width = 8      # A8 建议用于 burst 覆盖
        self.cov_model = MarbCoverageModel(addr_width=self.addr_width)

    def build_phase(self):
        self.logger.info("Start build_phase() -> MARB coverage collector")
        super().build_phase()
        self.logger.info("End build_phase() -> MARB coverage collector")

    def write(self, t: cl_sdt_seq_item):
        """
        analysis_export.write() 被调用时触发
        """
        if not isinstance(t, cl_sdt_seq_item):
            # 理论上不会发生，防御性检查一下
            self.logger.warning(f"Coverage collector received non-SDT item: {t}")
            return

        # 将 transaction 交给覆盖模型处理
        self.cov_model.sample_transaction(t)

    def final_phase(self):
        """
        仿真结束时把 coverage 写成 UCIS XML
        （路径可以根据需要改成 sim_build/<test-name>_cov.xml）
        """
        super().final_phase()

        try:
            # 这里给一个默认文件名，你可以在 test 里通过 ConfigDB 配置
            outfile = "sim_build/marb_cov.xml"
            self.logger.info(f"[COV] Writing UCIS coverage database to {outfile}")
            vsc.write_coverage_db(outfile)
        except Exception as e:
            self.logger.error(f"[COV] Failed to write coverage DB: {e}")
