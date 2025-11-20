import cocotb
from cocotb.triggers import RisingEdge
from cocotb.log import SimLog


class SDTProtocolChecker:
    def __init__(self, name, vif):
        self.name = name
        self.vif = vif

        # MUST use SimLog instead of Python logging
        self.logger = SimLog(f"SDT_CHECKER.{name}")
        self.logger.setLevel("INFO")

    async def start(self):
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
        while True:
            await RisingEdge(self.vif.clk)
            rd = int(self.vif.rd.value)
            wr = int(self.vif.wr.value)

            if rd and wr:
                self.logger.error("❌ RD and WR HIGH at same time!")
                raise AssertionError("RD ∧ WR violation")

    async def check_ack_requires_request(self):
        last_req = False
        while True:
            await RisingEdge(self.vif.clk)

            ack = int(self.vif.ack.value)
            rd = int(self.vif.rd.value)
            wr = int(self.vif.wr.value)

            if rd or wr:
                last_req = True

            if ack and not last_req:
                self.logger.error("❌ ACK without request!")
                raise AssertionError("ACK w/o request")

            if ack:
                last_req = False

    async def check_request_pulse(self):
        prev_rd = 0
        prev_wr = 0

        while True:
            await RisingEdge(self.vif.clk)

            rd = int(self.vif.rd.value)
            wr = int(self.vif.wr.value)

            if prev_rd and rd:
                self.logger.error("❌ RD pulse > 1 cycle!")
                raise AssertionError("RD pulse > 1")

            if prev_wr and wr:
                self.logger.error("❌ WR pulse > 1 cycle!")
                raise AssertionError("WR pulse > 1")

            prev_rd = rd
            prev_wr = wr
