import vsc

from uvc.sdt.src import *
from cl_marb_tb_base_seq import cl_marb_tb_base_seq
from reg_model.seq_lib.cl_reg_setup_seq import cl_reg_setup_seq
from reg_model.seq_lib.cl_reg_static_seq import cl_reg_static_seq

@vsc.randobj
class cl_reg_simple_seq(cl_marb_tb_base_seq, object):
    """Setup and start Memory Arbiter with static configuration"""

    def __init__(self, name = "cl_reg_simple_seq"):
        cl_marb_tb_base_seq.__init__(self, name)
        object.__init__(self)

    async def body(self):
        await super().body()

        self.sequencer.logger.debug("Starting setup seq (reg_model/seq_lib/cl_reg_setup_seq.py)")
        setup_seq  = cl_reg_setup_seq.create("setup_seq")
        await setup_seq.start(self.sequencer)

        self.sequencer.logger.debug("Starting static seq (reg_model/seq_lib/cl_reg_static_seq.py)")
        static_seq = cl_reg_static_seq.create("static_seq")
        await static_seq.start(self.sequencer)