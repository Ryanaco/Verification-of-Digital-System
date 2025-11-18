from pyuvm import *
from cl_marb_ref_model import cl_marb_ref_model
from cl_marb_scoreboard import cl_marb_scoreboard


class cl_marb_tb_env(uvm_env):
    """MARB Testbench Environment with REF model + Scoreboard"""

    def build_phase(self):
        self.logger.info("🏗️ [BUILD] Building MARB Testbench Environment")
        super().build_phase()

        # 构建子组件
        self.ref_model = cl_marb_ref_model("ref_model", self)
        self.scoreboard = cl_marb_scoreboard("scoreboard", self)

        # 获取配置对象（如果在 base test 已设置）
        self.cfg = ConfigDB().get(self, "", "cfg")

        # 创建 SDT agents（如果未定义）
        if not hasattr(self, "sdt_cif_agents"):
            self.sdt_cif_agents = []
        if not hasattr(self, "sdt_mif_agent"):
            self.sdt_mif_agent = None

    def connect_phase(self):
        self.logger.info("🔗 [CONNECT] Connecting REF model and Scoreboard")
        super().connect_phase()

        # ============================
        # 1️⃣ CIF request_ap → REF model
        # ============================
        for i, agent in enumerate(self.sdt_cif_agents):
            if hasattr(agent, "request_ap"):
                self.logger.info(f"📡 Connecting CIF{i}.request_ap → REF model.analysis_export")
                agent.request_ap.connect(self.ref_model.analysis_export)
            else:
                self.logger.warning(f"⚠️ CIF{i} has no request_ap defined")

        # ============================
        # 2️⃣ REF model → Scoreboard
        # ============================
        self.logger.info("📡 Connecting REF model.ref_ap → Scoreboard.ref_export")
        self.ref_model.ref_ap.connect(self.scoreboard.ref_export)

        # ============================
        # 3️⃣ DUT output (MIF.ap) → Scoreboard
        # ============================
        if self.sdt_mif_agent and hasattr(self.sdt_mif_agent, "ap"):
            self.logger.info("📡 Connecting MIF.ap → Scoreboard.dut_export")
            self.sdt_mif_agent.ap.connect(self.scoreboard.dut_export)
        else:
            self.logger.warning("⚠️ MIF agent or ap missing, cannot connect DUT output.")
