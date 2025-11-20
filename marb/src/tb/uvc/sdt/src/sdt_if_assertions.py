import cocotb
from cocotb.triggers import RisingEdge
import logging
import logging
logging.basicConfig(level=logging.INFO)

class SDTProtocolChecker:
    def __init__(self, name, vif):
        self.name = name
        self.vif = vif
        self.logger = logging.getLogger(f"SDT_CHECKER.{name}")

    async def start(self):
        self.logger.info(f"[CHECKER] {self.name} started.")
        print(f"=== SDT CHECKER STARTED for {self.name} ===")
        self.logger.info(
            f"[CHECKER] Connected signals: "
            f"rd={self.vif.rd._name}, wr={self.vif.wr._name}, "
            f"addr={self.vif.addr._name}, ack={self.vif.ack._name}"
        )

        # Optional: heartbeat
        cocotb.start_soon(self._heartbeat())

        # 启动所有检查器
        cocotb.start_soon(self.check_rd_wr_mutual_exclusion())
        cocotb.start_soon(self.check_ack_requires_request())
        cocotb.start_soon(self.check_request_pulse())

    async def _heartbeat(self):
        while True:
            await RisingEdge(self.vif.clk)
            self.logger.debug(f"[CHECKER] {self.name} alive...")

    # ---------------------------------------------------
    # 规则 1：RD/WR 不能同时为 1
    # ---------------------------------------------------
    async def check_rd_wr_mutual_exclusion(self):
        while True:
            await RisingEdge(self.vif.clk)

            rd = int(self.vif.rd.value)
            wr = int(self.vif.wr.value)

            self.logger.debug(f"[CHECKER] rd={rd} wr={wr}")

            if rd and wr:
                self.logger.error(
                    f"❌ [SDT ERROR] RD and WR are HIGH simultaneously!"
                )
                raise AssertionError("SDT protocol violation: RD ∧ WR")

    # ---------------------------------------------------
    # 规则 2：ACK 必须在 RD 或 WR 之后才能出现
    # ---------------------------------------------------
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
                self.logger.error(
                    f"❌ [SDT ERROR] ACK received without prior request!"
                )
                raise AssertionError("SDT protocol violation: ACK w/o request")

            if ack:
                last_req = False

    # ---------------------------------------------------
    # 规则 3：请求（RD/WR）必须是 1-cycle 脉冲
    # ---------------------------------------------------
    async def check_request_pulse(self):
        prev_rd = 0
        prev_wr = 0

        while True:
            await RisingEdge(self.vif.clk)

            rd = int(self.vif.rd.value)
            wr = int(self.vif.wr.value)

            # 检查 multi-cycle 脉冲
            if prev_rd and rd:
                self.logger.error(
                    f"❌ [SDT ERROR] RD request lasted longer than 1 cycle!"
                )
                raise AssertionError("SDT protocol violation: RD pulse > 1")

            if prev_wr and wr:
                self.logger.error(
                    f"❌ [SDT ERROR] WR request lasted longer than 1 cycle!"
                )
                raise AssertionError("SDT protocol violation: WR pulse > 1")

            prev_rd = rd
            prev_wr = wr