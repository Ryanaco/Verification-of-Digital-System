from pyuvm import *
from collections import deque


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
        self.rd_data_queue = deque()
        self.wr_data_queue = deque()

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
            self.logger.info(f"🟦 SDT CIF{i} agent instantiated")

        # ---- 实例化 MIF Agent ----
        self.sdt_mif_agent = cl_sdt_agent("mif_agent", self)
        mif_cfg = self.cfg.sdt_mif_cfg

        ConfigDB().set(self, "mif_agent", "cfg", mif_cfg)
        ConfigDB().set(self, "mif_agent.driver", "cfg", mif_cfg)
        ConfigDB().set(self, "mif_agent.monitor", "cfg", mif_cfg)
        ConfigDB().set(self, "mif_agent.sequencer", "cfg", mif_cfg)

        self.logger.info("🟩 SDT MIF agent instantiated")

    def connect_phase(self):
        super().connect_phase()
        self.logger.info("🔗 [CONNECT] Starting connect_phase()")

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

        self.logger.info("🚫 REF Model / Scoreboard skipped for A3–A4")
