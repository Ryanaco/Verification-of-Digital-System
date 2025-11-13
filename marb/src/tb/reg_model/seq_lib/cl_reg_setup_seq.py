from pyuvm import *
from .cl_reg_base_seq import *


class cl_reg_setup_seq(cl_reg_base_seq):
    """Setup sequence for control registers"""

    def __init__(self, name="cl_reg_setup_seq"):
        super().__init__(name)

    async def body(self):
        await super().body()

        #######################
        #  Start setup sequence
        #######################
        self.sequencer.logger.debug("Starting setup sequence for dprio_reg")

        # ✅ 显式获取 map （pyuvm 目前必须传 map 参数）
        reg_map = self.sequencer.reg_model.bus_map

        # ✅ Read
        status, read_val = await self.sequencer.reg_model.dprio_reg.read(
            reg_map, path_t.FRONTDOOR, check_t.NO_CHECK
        )

        if status == status_t.IS_OK:
            self.sequencer.logger.info(
                f"Setup SEQ: read {read_val:#010x} from dprio_reg, status = {status}"
            )
        else:
            self.sequencer.logger.error("Setup SEQ: STATUS is NOT_OK")

        # ✅ Write
        write_val = 0x00000000
        status = await self.sequencer.reg_model.dprio_reg.write(
            write_val, reg_map, path_t.FRONTDOOR, check_t.NO_CHECK
        )

        if status == status_t.IS_OK:
            self.sequencer.logger.info(
                f"Setup SEQ: written {write_val:#010x} to dprio_reg, status = {status}"
            )
        else:
            self.sequencer.logger.error("Setup SEQ: STATUS is NOT_OK")
