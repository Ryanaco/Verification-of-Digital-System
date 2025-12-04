from .cl_reg_base_seq import *

class cl_reg_static_seq(cl_reg_base_seq):
    """Setup sequence for registers"""

    def __init__(self, name = "cl_reg_static_seq"):
        super().__init__(name)

    async def body(self):
        await super().body()

        #######################
        # Set static priority
        #######################

        # set fixed priority
        # cif0 > cif1 > cif2
        status, read_val = await self.sequencer.reg_model.ctrl_reg.read(self.bus_map, path_t.FRONTDOOR, check_t.NO_CHECK)
        # Check the status received
        if status == status_t.IS_OK:
            self.sequencer.logger.info(
                f"Static SEQ: read {read_val} "
                f"from ctrl_reg, status = {status}")
        else:
            self.sequencer.logger.error("STATUS is NOT_OK")

        write_val = read_val | self.start_mask
        status = await self.sequencer.reg_model.ctrl_reg.write(write_val, self.bus_map, path_t.FRONTDOOR, check_t.NO_CHECK)
        # Check the status received
        if status == status_t.IS_OK:
            self.sequencer.logger.info(
                f"Static SEQ: written {write_val} "
                f"to ctrl_reg, status = {status}")
        else:
            self.sequencer.logger.error("STATUS is NOT_OK")