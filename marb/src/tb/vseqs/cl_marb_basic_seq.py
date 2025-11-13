from uvc.sdt.src import *
from cl_marb_tb_base_seq import cl_marb_tb_base_seq

class cl_marb_basic_seq(cl_marb_tb_base_seq):
    """Start virutal sequence of rd and wr in parallel for each producer"""

    def __init__(self, name = "cl_marb_basic_seq"):
        super().__init__(name)

    async def body(self):
        self.sequencer.logger.info("STARTING SUPER:BODY")
        await super().body()

        self.sequencer.logger.info("STARTING STARTING SEQUENCES")
