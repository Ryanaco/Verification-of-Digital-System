"""SDT-UVC Coverage collector"""

import vsc
from pyuvm import uvm_subscriber, ConfigDB
from .sdt_common import AccessType

class cl_sdt_coverage(uvm_subscriber):
    def __init__(self, name, parent):
        super().__init__(name, parent)

        # Handle to the configuration object
        self.cfg  = None

    def build_phase(self):
        self.logger.info("Start build_phase() -> SDT coverage")
        super().build_phase()

        # Get the configuration object
        self.cfg = ConfigDB().get(self, "", "cfg")

        self.cg_fulltrans = covergroup_fulltrans(f"{self.get_full_name()}.cg_fulltrans")
        self.cg_delays = covergroup_delays(f"{self.get_full_name()}.cg_delays")

        self.logger.info("End build_phase() -> SDT coverage")

    def write(self, item):
        access = 0 if item.access == AccessType.RD else 1
        addr = item.addr
        data = item.data
        consumer_delay_rdwr1_ack1 = item.consumer_delay_rdwr1_ack1

        if self.cfg.enable_transaction_coverage:
                self.logger.debug(f"Sample fulltrans: access = {access}, addr = {addr}, data = {data}")
                self.cg_fulltrans.sample(access, addr, data)
        if self.cfg.enable_delay_coverage:
            self.logger.debug(f"Sample delay: consumer_delay_rdwr1_ack1 = {consumer_delay_rdwr1_ack1}")
            self.cg_delays.sample(consumer_delay_rdwr1_ack1)


@vsc.covergroup
class covergroup_fulltrans(object):
    def __init__(self, name):
        self.options.name = name
        self.options.per_instance = True

        self.with_sample(
            access = vsc.bit_t(1),
            addr = vsc.bit_t(8),
            data = vsc.bit_t(8))

        self.fulltrans_access = vsc.coverpoint(self.access, bins = {
            "RD" :  vsc.bin(0),
            "WR" :  vsc.bin(1)})

        self.fulltrans_addr = vsc.coverpoint(self.addr, bins = {
            "low"  :  vsc.bin([  0,  84]),
            "med"  :  vsc.bin([ 85, 169]),
            "high" :  vsc.bin([170, 255])})

        self.fulltrans_data = vsc.coverpoint(self.data, bins = {
            "low"  :  vsc.bin([  0,  84]),
            "med"  :  vsc.bin([ 85, 169]),
            "high" :  vsc.bin([170, 255])})

        self.fulltrans_cross = vsc.cross(
            [self.fulltrans_access, self.fulltrans_addr, self.fulltrans_data])

@vsc.covergroup
class covergroup_delays(object):
    def __init__(self, name):
        self.name = name
        self.with_sample(
            cons_delay = vsc.int32_t())

        self.consumer_delay_rdwr1_ack1 = vsc.coverpoint(self.cons_delay, bins = {
            "0"      :  vsc.bin(0),
            "[1,5]"  :  vsc.bin([ 1,  5]),
            "[6,15]" :  vsc.bin([ 6, 15]),
            ">15"    :  vsc.bin([16, 50])})