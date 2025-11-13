""" SSDT-UVC Driver

- The UVM Driver is an active entity that converts abstract transaction to design pin toggles and vice-versa.
- Transaction level objects are obtained from the Sequencer and the UVM Driver drives them to the design via an interface handler, and vice-versa.
"""

from pyuvm import uvm_driver, ConfigDB

class uvc_ssdt_base_driver(uvm_driver):
    """ Driver for the SSDT-UVC.
        - translates transactions to pin level activity.
        - transactions pulled from sequencer by the seq_item_port.
    """
    def __init__(self, name = "uvc_driver", parent = None):

        super().__init__(name, parent)

        # Declaration of components
        self.cfg = None         # Configuration object
        self.vif = None         # Virtual interface object

    def build_phase(self):

        self.logger.debug("build_phase() Driver")
        super().build_phase()

        # Get the configuration object
        self.cfg = ConfigDB().get(self, "", "cfg")

        # Create an instance of Virtual interface (obtained from the ConfigDB)
        self.vif = self.cfg.vif

    async def run_phase(self):
        """ Run task of the Driver.
        """
        await super().run_phase()

        self.logger.info("Running driver...")

        while True:
            self.logger.debug(f"{'='*50}")

            # 1. Get(Wait for) next item
            self.logger.debug("Waiting for next seq_item...")
            self.req = await self.seq_item_port.get_next_item()
            self.logger.debug(f"Seq. item got: {self.req}")
            self.logger.debug(f"{'-'*50}")

            # 2. Once it get the transaction from the sequencer, clones it
            self.rsp = self.req.clone()
            # Set response_id
            self.rsp.set_context(self.req)
            # Set the transaction ID
            self.rsp.set_id_info(self.req)

            # 3. Drive transaction
            self.logger.debug("...Driving pins...")
            await self.drive_transaction()

            self.seq_item_port.item_done()
            self.logger.debug("item_done()")

            self.logger.debug(f"Putting response: {self.rsp}")
            self.seq_item_port.put_response(self.rsp)
            self.logger.debug("Response put.")

    async def drive_transaction(self):
        # Start driver
            await self.driver_loop()

    async def driver_loop(self):
        self.logger.info("sSDT base driver - drive_loop task")