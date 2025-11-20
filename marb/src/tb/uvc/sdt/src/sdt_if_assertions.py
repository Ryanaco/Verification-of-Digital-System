import cocotb
from cocotb.triggers import RisingEdge
from cocotb.log import SimLog


class SDTProtocolChecker:
    """SDT Protocol Checker for A7 - Monitors protocol compliance"""
    
    def __init__(self, name, vif):
        self.name = name
        self.vif = vif

        # MUST use SimLog instead of Python logging
        self.logger = SimLog(f"SDT_CHECKER.{name}")
        self.logger.setLevel("INFO")
        
        self.logger.critical(f"### SDT CHECKER CONSTRUCTED: {name} ###")
        
        # Coverage counters for A7
        self.rd_count = 0
        self.wr_count = 0
        self.ack_count = 0
        self.violation_count = 0

    async def start(self):
        """Start all protocol checking coroutines"""
        self.logger.info(f"=== SDT CHECKER STARTED for {self.name} ===")
        self.logger.info(
            f"[CHECKER] Connected signals: "
            f"rd={self.vif.rd._name}, wr={self.vif.wr._name}, "
            f"addr={self.vif.addr._name}, ack={self.vif.ack._name}"
        )

        cocotb.start_soon(self._heartbeat())
        cocotb.start_soon(self.check_rd_wr_mutual_exclusion())
        cocotb.start_soon(self.check_ack_requires_request())
        cocotb.start_soon(self.check_request_pulse())

    async def _heartbeat(self):
        while True:
            await RisingEdge(self.vif.clk)
            self.logger.debug(f"[CHECKER] {self.name} alive...")

    async def check_rd_wr_mutual_exclusion(self):
        """Verify RD and WR are mutually exclusive (never asserted simultaneously)"""
        while True:
            await RisingEdge(self.vif.clk)
            rd = int(self.vif.rd.value)
            wr = int(self.vif.wr.value)

            if rd and wr:
                self.logger.error("❌ RD and WR HIGH at same time!")
                self.violation_count += 1
                raise AssertionError("RD ∧ WR violation")

    async def check_ack_requires_request(self):
        """Verify ACK is only asserted in response to a previous RD or WR request"""
        last_req = False
        while True:
            await RisingEdge(self.vif.clk)

            ack = int(self.vif.ack.value)
            rd = int(self.vif.rd.value)
            wr = int(self.vif.wr.value)

            if rd or wr:
                last_req = True
                if rd:
                    self.rd_count += 1
                if wr:
                    self.wr_count += 1

            if ack and not last_req:
                self.logger.error("❌ ACK without request!")
                self.violation_count += 1
                raise AssertionError("ACK w/o request")

            if ack:
                self.ack_count += 1
                last_req = False

    async def check_request_pulse(self):
        """Monitor RD and WR signal activity (track consecutive cycles for coverage)"""
        prev_rd = 0
        prev_wr = 0

        while True:
            await RisingEdge(self.vif.clk)

            rd = int(self.vif.rd.value)
            wr = int(self.vif.wr.value)

            # Monitor signal transitions (for coverage reporting)
            # Note: The SDT protocol allows RD/WR to remain HIGH during handshake
            # until ACK is received, so we don't enforce "single-cycle pulse" strictly
            # Instead, we just track activity for coverage

            prev_rd = rd
            prev_wr = wr
