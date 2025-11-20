from pyuvm import *
from queue import Queue
from cl_marb_ref_model import cl_marb_ref_model
from cl_marb_scoreboard import cl_marb_scoreboard


class cl_marb_tb_env(uvm_env):
    """
    Fully Functional MARB Environment (A2 + A5 compliant)
    Includes:
        - 3 CIF SDT Agents
        - 1 MIF SDT Agent
        - APB Agent (由 base_test 实例化并挂到 env 上)
        - Virtual Sequencer
        - Reference Model (A5)
        - Scoreboard (A6)
    """

    def build_phase(self):
        super().build_phase()
        self.logger.info("🏗️ [BUILD] Building MARB Testbench Environment")

        # 从 Base Test 获取 config
        self.cfg = ConfigDB().get(self, "", "cfg")

        # ---- FIFO queues for SDT drivers ----
        self.rd_data_queue = Queue()
        self.wr_data_queue = Queue()

        for i in range(3):
            ConfigDB().set(self, f"cif{i}_agent.driver", "rd_data_queue", self.rd_data_queue)
            ConfigDB().set(self, f"cif{i}_agent.driver", "wr_data_queue", self.wr_data_queue)

        ConfigDB().set(self, "mif_agent.driver", "rd_data_queue", self.rd_data_queue)
        ConfigDB().set(self, "mif_agent.driver", "wr_data_queue", self.wr_data_queue)

        # ---- Virtual sequencer ----
        self.virtual_sequencer = uvm_sequencer("virtual_sequencer", self)

        # ---- SDT CIF Agents ----
        from uvc.sdt.src.cl_sdt_agent import cl_sdt_agent
        self.sdt_cif_agents = []

        for i, cif_cfg in enumerate(self.cfg.sdt_cif_cfgs):
            agent = cl_sdt_agent(f"cif{i}_agent", self)

            ConfigDB().set(self, f"cif{i}_agent", "cfg", cif_cfg)
            ConfigDB().set(self, f"cif{i}_agent.driver", "cfg", cif_cfg)
            ConfigDB().set(self, f"cif{i}_agent.monitor", "cfg", cif_cfg)
            ConfigDB().set(self, f"cif{i}_agent.sequencer", "cfg", cif_cfg)

            self.sdt_cif_agents.append(agent)
            setattr(self, f"cif{i}_agent", agent)

            self.logger.info(f"🟦 SDT CIF{i} agent instantiated")

        # ---- MIF SDT Agent ----
        self.sdt_mif_agent = cl_sdt_agent("mif_agent", self)
        mif_cfg = self.cfg.sdt_mif_cfg
        ConfigDB().set(self, "mif_agent", "cfg", mif_cfg)
        ConfigDB().set(self, "mif_agent.driver", "cfg", mif_cfg)
        ConfigDB().set(self, "mif_agent.monitor", "cfg", mif_cfg)
        ConfigDB().set(self, "mif_agent.sequencer", "cfg", mif_cfg)

        self.logger.info("🟩 SDT MIF agent instantiated")

        # ---- Reference Model ----
        self.logger.info("🧠 Creating Reference Model...")
        self.ref_model = cl_marb_ref_model("ref_model", self)
        self.logger.info("✅ Reference Model instantiated")

        # ---- Scoreboard ----
        self.logger.info("📊 Creating Scoreboard...")
        self.scoreboard = cl_marb_scoreboard("scoreboard", self)
        self.logger.info("✅ Scoreboard instantiated")

    # ===================================================================
    # CONNECT PHASE
    # ===================================================================
    def connect_phase(self):
        super().connect_phase()
        self.logger.info("🔗 [CONNECT] Starting connect_phase()")

        # ---------------------------
        # SDT CIF VIF connections
        # ---------------------------
        for i, agent in enumerate(self.sdt_cif_agents):
            agent.driver.vif = self.cfg.sdt_cif_cfgs[i].vif
            agent.monitor.vif = self.cfg.sdt_cif_cfgs[i].vif
            self.logger.info(f"✅ CIF{i} VIF connected")

        # ---------------------------
        # MIF VIF connections
        # ---------------------------
        self.sdt_mif_agent.driver.vif = self.cfg.sdt_mif_cfg.vif
        self.sdt_mif_agent.monitor.vif = self.cfg.sdt_mif_cfg.vif
        self.logger.info("✅ MIF VIF connected")

        # ---------------------------
        # Sequencers → Virtual sequencer
        # ---------------------------
        self.virtual_sequencer.cif_seqrs = [
            agent.sequencer for agent in self.sdt_cif_agents
        ]
        self.virtual_sequencer.apb_seqr = self.apb_agent.sequencer

        # ===================================================================
        # ANALYSIS PORT CONNECTIONS (PyUVM 正确写法！)
        # ===================================================================

        self.logger.info("🔗 Connecting analysis ports...")

        # CIF request_ap → ref_model.analysis_export
        for i, agent in enumerate(self.sdt_cif_agents):
            if hasattr(agent.monitor, "request_ap"):
                agent.monitor.request_ap.connect(self.ref_model.analysis_export)
                self.logger.info(f"📡 CIF{i} request_ap → ref_model.analysis_export")

        # APB monitor.ap → ref_model.analysis_export
        if hasattr(self.apb_agent.monitor, "ap"):
            self.apb_agent.monitor.ap.connect(self.ref_model.analysis_export)
            self.logger.info("📡 APB.ap → ref_model.analysis_export (A5 requirement)")

        # MIF monitor.ap → scoreboard.dut_subscriber
        self.sdt_mif_agent.monitor.ap.connect(
            self.scoreboard.dut_subscriber.analysis_export
        )
        self.logger.info("📡 MIF.ap → scoreboard.dut_subscriber")

        # ref_model.ref_ap → scoreboard.ref_subscriber
        self.ref_model.ref_ap.connect(self.scoreboard.ref_subscriber.analysis_export)
        self.logger.info("📡 ref_model.ref_ap → scoreboard.ref_subscriber")

        self.logger.info("✅ [CONNECT] Finished connect_phase()")
