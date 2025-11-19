from pyuvm import *


class cl_marb_tb_env(uvm_env):
    """
    MARB Testbench Environment (Clean A3–A4 version)
    - NO reference model
    - NO scoreboard
    - Includes:
        * CIF SDT agents
        * MIF SDT agent
        * APB agent
        * Virtual Sequencer (with CIF + APB sequencers)
    """

    def build_phase(self):
        super().build_phase()
        self.logger.info("🏗️ [BUILD] Building MARB Clean Testbench Environment")

        # -------------------------------------------------------
        # 配置对象（从 base test 注入）
        # -------------------------------------------------------
        self.cfg = ConfigDB().get(self, "", "cfg")

        # -------------------------------------------------------
        # Virtual Sequencer （A4 必须）
        # -------------------------------------------------------
        self.virtual_sequencer = uvm_sequencer("virtual_sequencer", self)

        # -------------------------------------------------------
        # 占位：这些会在 base_test 里注入
        # -------------------------------------------------------
        if not hasattr(self, "sdt_cif_agents"):
            self.sdt_cif_agents = []    # list of 3 CIF agents

        if not hasattr(self, "sdt_mif_agent"):
            self.sdt_mif_agent = None   # MIF SDT agent

        if not hasattr(self, "apb_agent"):
            self.apb_agent = None       # APB agent

    # -------------------------------------------------------
    # CONNECT PHASE
    # -------------------------------------------------------
    def connect_phase(self):
        super().connect_phase()
        self.logger.info("🔗 [CONNECT] Connecting Clean MARB Testbench Components")

        # -------------------------------------------------------
        # 1. CIF SDT sequencers → Virtual Sequencer
        # -------------------------------------------------------
        self.virtual_sequencer.cif_seqrs = []

        for i, agent in enumerate(self.sdt_cif_agents):
            if hasattr(agent, "sequencer"):
                self.virtual_sequencer.cif_seqrs.append(agent.sequencer)
                self.logger.info(f"📡 CIF{i} sequencer → Virtual Sequencer")
            else:
                self.logger.error(f"❌ CIF{i} has no sequencer!")

        # -------------------------------------------------------
        # 2. APB sequencer → Virtual Sequencer
        # -------------------------------------------------------
        if self.apb_agent and hasattr(self.apb_agent, "sequencer"):
            self.virtual_sequencer.apb_seqr = self.apb_agent.sequencer
            self.logger.info("📡 APB sequencer → Virtual Sequencer")
        else:
            self.logger.error("❌ APB agent not connected or missing sequencer")

        # -------------------------------------------------------
        # 3. 不连接 REF 或 Scoreboard（A5/A6 禁用）
        # -------------------------------------------------------
        self.logger.info("🚫 Reference Model / Scoreboard disabled for A3–A4")
