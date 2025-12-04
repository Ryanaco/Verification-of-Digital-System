# cl_marb_coverage.py
#
# MARB coverage collector
#
# - Acts as a uvm_subscriber connected to the MIF monitor analysis port
# - Uses PyVSC for functional coverage and exports UCIS
#
# Requirements:
#   1) Inherit from uvm_subscriber and attach to MIF monitor
#   2) Coverage: WR followed by RD on the same address (back-to-back or non-consecutive)
#   3) Burst coverage: longest sequence of consecutive addresses, and cross (start × length)
#   4) Perform sampling for every transaction in write()
#

from pyuvm import *
import vsc

# SDT UVC transaction and access type
from uvc.sdt.src.cl_sdt_seq_item import cl_sdt_seq_item
from uvc.sdt.src.sdt_common import AccessType


# ---------------------------------------------------------
#  Covergroup Definitions
# ---------------------------------------------------------

@vsc.covergroup
class WrRdSameAddrB2BCg(object):
    """
    Coverage: Back-to-back WR followed immediately by RD on the same address.
    - coverpoint: address
    - One bin per address using bin_array
    """
    def __init__(self, addr_getter, addr_max):
        self.cp_addr = vsc.coverpoint(
            addr_getter,
            bins={
                "addr": vsc.bin_array([], [0, addr_max])
            }
        )


@vsc.covergroup
class WrRdSameAddrNonConsecCg(object):
    """
    Coverage: Non-consecutive WR followed by RD on the same address.
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
    Coverage for burst detection:
    - coverpoint: burst_start_addr
    - coverpoint: burst_len
    - cross: start × length
    """
    def __init__(self, start_addr_getter, length_getter, addr_max):
        self.cp_start = vsc.coverpoint(
            start_addr_getter,
            bins={
                "start": vsc.bin_array([], [0, addr_max])
            }
        )

        max_len = addr_max + 1
        self.cp_len = vsc.coverpoint(
            length_getter,
            bins={
                "len": vsc.bin_array([], [1, max_len])
            }
        )

        self.start_x_len = vsc.cross([self.cp_start, self.cp_len])


# ---------------------------------------------------------
#  Pure Python Coverage Model: internal state tracking + CG sampling
# ---------------------------------------------------------

class MarbCoverageModel:
    """
    Internal coverage model updated from MIF monitor cl_sdt_seq_item transactions.
    """

    def __init__(self, addr_width=8):
        self.addr_width = addr_width
        self.addr_max = (1 << addr_width) - 1

        # ---- WR-RD same address state ----
        self.last_access_addr = None
        self.last_access_is_wr = False

        # Non-consecutive WR->RD tracking
        self.written_addr_set = set()

        # ---- Burst tracking state ----
        self.burst_active = False
        self.burst_start_addr = 0
        self.burst_len = 0
        self.burst_prev_addr = None

        # ---- Variables sampled by covergroups ----
        self.curr_addr_for_wr_rd = 0
        self.curr_burst_start = 0
        self.curr_burst_len = 0

        # ---- Instantiate covergroups ----
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
    #  Main interface: sample a transaction
    # -------------------------------
    def sample_transaction(self, item: cl_sdt_seq_item):
        """
        Perform all coverage sampling for a single cl_sdt_seq_item.
        """
        if item.addr is None:
            return

        addr = int(item.addr)
        access = int(item.access)

        is_wr = (access == int(AccessType.WR))
        is_rd = (access == int(AccessType.RD))

        # 1) WR-RD same address coverage
        self._sample_wr_rd_same_addr(addr, is_wr, is_rd)

        # 2) Burst coverage (only WR contributes to burst)
        self._update_and_sample_burst(addr, is_wr, is_rd)

    # -------------------------------
    #  1) WR->RD same address
    # -------------------------------
    def _sample_wr_rd_same_addr(self, addr: int, is_wr: bool, is_rd: bool):
        # Back-to-back WR -> RD same address
        if (
            self.last_access_is_wr
            and is_rd
            and self.last_access_addr is not None
            and addr == self.last_access_addr
        ):
            self.curr_addr_for_wr_rd = addr
            self.wr_rd_b2b_cg.sample()

        # Non-consecutive WR->RD same address
        if is_wr:
            self.written_addr_set.add(addr)

        if is_rd and addr in self.written_addr_set:
            self.curr_addr_for_wr_rd = addr
            self.wr_rd_nonconsec_cg.sample()
            # Keep the address in the set (can hit multiple times)

        # Update last access status
        if is_wr or is_rd:
            self.last_access_addr = addr
            self.last_access_is_wr = is_wr

    # -------------------------------
    #  2) Burst detection (sequential addresses on WR)
    # -------------------------------
    def _update_and_sample_burst(self, addr: int, is_wr: bool, is_rd: bool):
        if not is_wr:
            # If burst active, close and sample
            if self.burst_active and self.burst_len > 0:
                self._sample_current_burst()
            return

        # Current access is WR
        if not self.burst_active:
            self.burst_active = True
            self.burst_start_addr = addr
            self.burst_prev_addr = addr
            self.burst_len = 1
            return

        expected_next = (self.burst_prev_addr + 1) & self.addr_max

        if addr == expected_next:
            # Continue the burst
            self.burst_len += 1
            self.burst_prev_addr = addr
        else:
            # Burst interrupted — sample current burst and start new one
            self._sample_current_burst()
            self.burst_active = True
            self.burst_start_addr = addr
            self.burst_prev_addr = addr
            self.burst_len = 1

    def _sample_current_burst(self):
        """
        Feed current burst_start_addr and burst_len to the covergroup.
        """
        if self.burst_len <= 0:
            return

        self.curr_burst_start = int(self.burst_start_addr)
        self.curr_burst_len = int(self.burst_len)
        self.burst_cg.sample()

        # Reset burst state
        self.burst_active = False
        self.burst_len = 0
        self.burst_prev_addr = None


# ---------------------------------------------------------
#  Coverage Collector: UVM subscriber
# ---------------------------------------------------------

class cl_marb_coverage_collector(uvm_subscriber):
    """
    - Inherits from uvm_subscriber
    - Receives cl_sdt_seq_item from MIF monitor via analysis_export
    - Uses MarbCoverageModel to perform sampling
    """

    def __init__(self, name, parent):
        super().__init__(name, parent)

        self.addr_width = 8  # Suggested width for burst coverage
        self.cov_model = MarbCoverageModel(addr_width=self.addr_width)

    def build_phase(self):
        self.logger.info("Start build_phase() -> MARB coverage collector")
        super().build_phase()
        self.logger.info("End build_phase() -> MARB coverage collector")

    def write(self, t: cl_sdt_seq_item):
        """
        Triggered when analysis_export.write() is called.
        """
        if not isinstance(t, cl_sdt_seq_item):
            self.logger.warning(f"Coverage collector received non-SDT item: {t}")
            return

        # Forward transaction to the internal coverage model
        self.cov_model.sample_transaction(t)

    def final_phase(self):
        """
        Write out UCIS coverage DB at end of simulation.
        """
        super().final_phase()

        try:
            outfile = "sim_build/marb_cov.xml"
            self.logger.info(f"[COV] Writing UCIS coverage database to {outfile}")
            vsc.write_coverage_db(outfile)
        except Exception as e:
            self.logger.error(f"[COV] Failed to write coverage DB: {e}")
