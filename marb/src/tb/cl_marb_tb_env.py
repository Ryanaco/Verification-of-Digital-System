from pyuvm import *
from queue import Queue
from cl_marb_ref_model import cl_marb_ref_model
from cl_marb_scoreboard import cl_marb_scoreboard


class cl_marb_tb_env(uvm_env):
    """
    Fully Functional MARB Environment (A2 compliant)
    Includes:
        - 3 CIF SDT Agents
        - 1 MIF SDT Agent
        - APB Agent (由 base_test 实例化并挂到 env 上)
        - Virtual Sequencer
    """

    def build_phase(self):
        super().build_phase()
        self.logger.info("🏗️ [BUILD] Building MARB Testbench Environment")

        # 从 Base Test 拿到总配置对象
        self.cfg = ConfigDB().get(self, "", "cfg")

        # ---- 创建队列（供 SDT driver 使用）----
        #   cl_sdt_base_driver.build_phase() 中会：
        #     rd_data_queue = ConfigDB().get(self, '', 'rd_data_queue')
        #     wr_data_queue = ConfigDB().get(self, '', 'wr_data_queue')
        self.rd_data_queue = Queue()
        self.wr_data_queue = Queue()

        # ---- 在实例化 SDT agent 之前，为各 driver 设置 FIFO ----
        for i in range(3):
            ConfigDB().set(self, f"cif{i}_agent.driver", "rd_data_queue", self.rd_data_queue)
            ConfigDB().set(self, f"cif{i}_agent.driver", "wr_data_queue", self.wr_data_queue)

        ConfigDB().set(self, "mif_agent.driver", "rd_data_queue", self.rd_data_queue)
        ConfigDB().set(self, "mif_agent.driver", "wr_data_queue", self.wr_data_queue)

        # ---- 实例化 virtual sequencer ----
        self.virtual_sequencer = uvm_sequencer("virtual_sequencer", self)

        # ---- 实例化 SDT CIF Agents ----
        from uvc.sdt.src.cl_sdt_agent import cl_sdt_agent
        self.sdt_cif_agents = []

        for i, cif_cfg in enumerate(self.cfg.sdt_cif_cfgs):
            agent = cl_sdt_agent(f"cif{i}_agent", self)

            # 把每个 CIF 的 cl_sdt_config 下发给 agent/driver/monitor/sequencer
            ConfigDB().set(self, f"cif{i}_agent", "cfg", cif_cfg)
            ConfigDB().set(self, f"cif{i}_agent.driver", "cfg", cif_cfg)
            ConfigDB().set(self, f"cif{i}_agent.monitor", "cfg", cif_cfg)
            ConfigDB().set(self, f"cif{i}_agent.sequencer", "cfg", cif_cfg)

            self.sdt_cif_agents.append(agent)

            # ⭐ 新增：挂成属性，方便 test 用 self.marb_tb_env.cif0_agent 访问
            setattr(self, f"cif{i}_agent", agent)

            self.logger.info(f"🟦 SDT CIF{i} agent instantiated")

        # ---- 实例化 MIF Agent ----
        self.sdt_mif_agent = cl_sdt_agent("mif_agent", self)
        mif_cfg = self.cfg.sdt_mif_cfg

        ConfigDB().set(self, "mif_agent", "cfg", mif_cfg)
        ConfigDB().set(self, "mif_agent.driver", "cfg", mif_cfg)
        ConfigDB().set(self, "mif_agent.monitor", "cfg", mif_cfg)
        ConfigDB().set(self, "mif_agent.sequencer", "cfg", mif_cfg)

        self.logger.info("🟩 SDT MIF agent instantiated")

        # ---- 实例化 Reference Model ----
        self.logger.info("🧠 Creating Reference Model...")
        self.ref_model = cl_marb_ref_model("ref_model", self)
        self.logger.info("✅ Reference Model instantiated")

        # ---- 实例化 Scoreboard ----
        self.logger.info("📊 Creating Scoreboard...")
        self.scoreboard = cl_marb_scoreboard("scoreboard", self)
        self.logger.info("✅ Scoreboard instantiated")

    def connect_phase(self):
        super().connect_phase()
        self.logger.info("🔗 [CONNECT] Starting connect_phase()")

        # ---- 为所有 SDT CIF agents 设置 VIF ----
        for i, agent in enumerate(self.sdt_cif_agents):
            # 确保 driver 和 monitor 有 VIF
            if agent.driver:
                agent.driver.vif = self.cfg.sdt_cif_cfgs[i].vif
                agent.driver.cfg.vif = self.cfg.sdt_cif_cfgs[i].vif
                self.logger.info(f"✅ CIF{i} driver VIF set: {agent.driver.vif.name}")
            if agent.monitor:
                agent.monitor.vif = self.cfg.sdt_cif_cfgs[i].vif
                agent.monitor.cfg.vif = self.cfg.sdt_cif_cfgs[i].vif
                self.logger.info(f"✅ CIF{i} monitor VIF set: {agent.monitor.vif.name}")
            self.logger.info(f"📡 CIF{i} agent VIF connected")

        # ---- 为 MIF agent 设置 VIF ----
        if self.sdt_mif_agent.driver:
            self.sdt_mif_agent.driver.vif = self.cfg.sdt_mif_cfg.vif
            self.sdt_mif_agent.driver.cfg.vif = self.cfg.sdt_mif_cfg.vif
            self.logger.info(f"✅ MIF driver VIF set: {self.sdt_mif_agent.driver.vif.name}")
        if self.sdt_mif_agent.monitor:
            self.sdt_mif_agent.monitor.vif = self.cfg.sdt_mif_cfg.vif
            self.sdt_mif_agent.monitor.cfg.vif = self.cfg.sdt_mif_cfg.vif
            self.logger.info(f"✅ MIF monitor VIF set: {self.sdt_mif_agent.monitor.vif.name}")
        self.logger.info("📡 MIF agent VIF connected")

        # CIF sequencers → virtual sequencer
        self.virtual_sequencer.cif_seqrs = []
        for i, agent in enumerate(self.sdt_cif_agents):
            self.virtual_sequencer.cif_seqrs.append(agent.sequencer)
            self.logger.info(f"📡 CIF{i} sequencer → Virtual Sequencer")

        # APB sequencer → virtual sequencer
        if hasattr(self, "apb_agent") and hasattr(self.apb_agent, "sequencer"):
            self.virtual_sequencer.apb_seqr = self.apb_agent.sequencer
            self.logger.info("📡 APB sequencer → Virtual Sequencer")
        else:
            self.logger.error("❌ APB agent missing!")

        # ---- 连接 CIF monitors 的 request_ap 到 ref_model ----
        self.logger.info("🔗 Connecting analysis ports...")
        for i, agent in enumerate(self.sdt_cif_agents):
            if agent.monitor and hasattr(agent.monitor, "request_ap"):
                agent.monitor.request_ap.connect(self.ref_model.analysis_export)
                self.logger.info(f"📡 CIF{i} monitor request_ap → ref_model")

        # ---- 连接 MIF monitor 的 ap 到 scoreboard 的 dut_subscriber ----
        if self.sdt_mif_agent.monitor and hasattr(self.sdt_mif_agent.monitor, "ap"):
            self.sdt_mif_agent.monitor.ap.connect(self.scoreboard.dut_subscriber.analysis_export)
            self.logger.info("📡 MIF monitor ap → scoreboard.dut_subscriber")

        # ---- 连接 ref_model 的输出到 scoreboard 的 ref_subscriber ----
        if hasattr(self.ref_model, "ref_ap"):
            self.ref_model.ref_ap.connect(self.scoreboard.ref_subscriber.analysis_export)
            self.logger.info("📡 ref_model.ref_ap → scoreboard.ref_subscriber")

        self.logger.info("✅ [CONNECT] Finished connect_phase()")
