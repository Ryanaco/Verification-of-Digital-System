from pyuvm import *
from .cl_reg_base_seq import *
 
 
class cl_reg_setup_seq(cl_reg_base_seq):
    """Setup sequence for control registers"""
 
    def __init__(self, name = "cl_reg_setup_seq"):
        super().__init__(name)
 
    async def body(self):
        await super().body()
 
        #######################
        # Start setup sequence
        #######################
        # Read dprio_reg register
        self.sequencer.logger.debug("Starting setup sequence for dprio_reg in map, ", self.bus_map)
        status, read_val = await self.sequencer.reg_model.dprio_reg.read(self.bus_map, path_t.FRONTDOOR, check_t.NO_CHECK)
 
        # Check the status received
        if status == status_t.IS_OK:
            self.sequencer.logger.info(
                f"Setup SEQ: read {read_val} "
                f"from dprio_reg, status = {status}")
        else:
            self.sequencer.logger.error("STATUS is NOT_OK")
 
        # Write dprio_reg register, setting dprio_reg.f_cif* to 0
        # This will only have an effect if:
        #
        #   ctrl_reg.f_en == 1
        #   ctrl_reg.f_mode == 1
        #
        # So the DUT is enabled and dynnamic mode is chosen
        write_val = 0
        status = await self.sequencer.reg_model.dprio_reg.write(write_val, self.bus_map, path_t.FRONTDOOR, check_t.NO_CHECK)
        # Check the status received
        if status == status_t.IS_OK:
            self.sequencer.logger.info(
                f"Setup SEQ: written {write_val} "
                f"to dprio_reg, status = {status}")
        else:
            self.sequencer.logger.error("STATUS is NOT_OK")
 
        # Read ctrl_reg register
        status, read_val = await self.sequencer.reg_model.ctrl_reg.read(self.bus_map, path_t.FRONTDOOR, check_t.NO_CHECK)
        # Check the status received
        if status == status_t.IS_OK:
            self.sequencer.logger.info(
                f"Setup SEQ: read {read_val} "
                f"from ctrl_reg, status = {status}")
        else:
            self.sequencer.logger.error("STATUS is NOT_OK")
 
        # Write ctrl_reg register, setting:
        #
        #   ctrl_reg.f_en == 0 (Disable the DUT)
        #   ctrl_reg.f_mode == 0
        #
        read_val & (~self.start_mask)
        status = await self.sequencer.reg_model.ctrl_reg.write(write_val, self.bus_map, path_t.FRONTDOOR, check_t.NO_CHECK)
        # Check the status received
        if status == status_t.IS_OK:
            self.sequencer.logger.info(
                f"Setup SEQ: written {write_val} "
                f"to ctrl_reg, status = {status}")
        else:
            self.sequencer.logger.error("STATUS is NOT_OK")
