from pyuvm import *

from uvc.sdt.src import *
from uvc.apb.src.cl_apb_agent import cl_apb_agent
from uvc.apb.src.cl_apb_reg_adapter import cl_apb_reg_adapter

from cl_marb_tb_virtual_sequencer import cl_marb_tb_virtual_sequencer
from reg_model.cl_reg_block import cl_reg_block


class cl_marb_tb_env(uvm_env):
    def __init__(self, name, parent):
        super().__init__(name, parent)

        self.cfg = None
        self.virtual_sequencer = None
        self.reg_model = None
        self.adapter = None
        self.apb_agent = None

        # SDT Agents
        self.sdt_cif_agents = []  # 3 client agents
        self.sdt_mif_agent = None  # 1 memory agent

    def build_phase(self):
        self.logger.info("Start build_phase() -> MARB env")

        # ✅ 防止重复 build（pyuvm 在同一 test 层次可能会触发两次 build_phase）
        if hasattr(self, "sdt_cif_agents") and len(self.sdt_cif_agents) > 0:
            self.logger.warning("⚠️ SDT CIF agents already built, skipping rebuild.")
            return

        super().build_phase()

        # Get configuration
        self.cfg = ConfigDB().get(self, "", "cfg")

        # Create virtual sequencer
        ConfigDB().set(self, "virtual_sequencer", "cfg", self.cfg)
        self.virtual_sequencer = cl_marb_tb_virtual_sequencer.create("virtual_sequencer", self)

        # APB agent
        ConfigDB().set(self, "apb_agent", "cfg", self.cfg.apb_cfg)
        self.apb_agent = cl_apb_agent("apb_agent", self)

        # Register model + adapter
        self.reg_model = cl_reg_block("reg_block")
        self.reg_model.build()

        if not hasattr(self.reg_model, "bus_map") or self.reg_model.bus_map is None:
            if hasattr(self.reg_model, "default_map"):
                self.reg_model.bus_map = self.reg_model.default_map
            else:
                self.reg_model.bus_map = uvm_reg_map("default_map", self.reg_model)

        self.adapter = cl_apb_reg_adapter()
        self.virtual_sequencer.reg_model = self.reg_model

        # Instantiate 3 CIF SDT agents (clients)
        for i in range(3):
            ConfigDB().set(self, f"sdt_cif_agent_{i}", "cfg", self.cfg.sdt_cif_cfgs[i])
            agent = cl_sdt_agent(f"sdt_cif_agent_{i}", self)
            self.sdt_cif_agents.append(agent)

        # Instantiate 1 MIF SDT agent (memory)
        ConfigDB().set(self, "sdt_mif_agent", "cfg", self.cfg.sdt_mif_cfg)
        self.sdt_mif_agent = cl_sdt_agent("sdt_mif_agent", self)

        # 🩵 在 build_phase() 末尾绑定所有 SDT agent 的 VIF
        import cocotb
        dut = cocotb.top

        # 🧩 Python 构造的虚接口对象（包含 clk、rst、stable）
        class SDT_VIF:
            def __init__(self, clk, rst, stable, rd, wr, addr, wr_data, rd_data, ack):
                self.clk = clk          # 🕒 时钟信号
                self.rst = rst          # 🔁 复位信号
                self.stable = stable    # 🟢 系统稳定信号
                self.rd = rd
                self.wr = wr
                self.addr = addr
                self.wr_data = wr_data
                self.rd_data = rd_data
                self.ack = ack

        try:
            # 🩵 创建 Client VIFs（带 clk、rst、stable）
            vif_c0 = SDT_VIF(dut.clk, dut.rst, dut.stable, dut.c0_rd, dut.c0_wr, dut.c0_addr, dut.c0_wr_data, dut.c0_rd_data, dut.c0_ack)
            vif_c1 = SDT_VIF(dut.clk, dut.rst, dut.stable, dut.c1_rd, dut.c1_wr, dut.c1_addr, dut.c1_wr_data, dut.c1_rd_data, dut.c1_ack)
            vif_c2 = SDT_VIF(dut.clk, dut.rst, dut.stable, dut.c2_rd, dut.c2_wr, dut.c2_addr, dut.c2_wr_data, dut.c2_rd_data, dut.c2_ack)

            # 🧠 Memory interface VIF
            vif_m  = SDT_VIF(dut.clk, dut.rst, dut.stable, dut.m_rd, dut.m_wr, dut.m_addr, dut.m_wr_data, dut.m_rd_data, dut.m_ack)

            # ✅ 注册到 ConfigDB
            ConfigDB().set(None, "uvm_test_top.marb_tb_env.sdt_cif_agent_0", "vif", vif_c0)
            ConfigDB().set(None, "uvm_test_top.marb_tb_env.sdt_cif_agent_1", "vif", vif_c1)
            ConfigDB().set(None, "uvm_test_top.marb_tb_env.sdt_cif_agent_2", "vif", vif_c2)
            ConfigDB().set(None, "uvm_test_top.marb_tb_env.sdt_mif_agent",    "vif", vif_m)

            self.logger.info("✅ SDT agent VIFs bound successfully (Python wrappers + clk + rst + stable)")
        except AttributeError as e:
            self.logger.error(f"❌ Failed to bind VIFs from DUT: {e}")
            raise

        self.logger.info("End build_phase() -> MARB env")
        ConfigDB().set(None, "", "reg_model", self.reg_model)

    def connect_phase(self):
        self.logger.info("Start connect_phase() -> MARB env")
        super().connect_phase()

        # Connect register model to APB agent
        self.reg_model.bus_map.set_sequencer(self.apb_agent.sequencer)
        self.reg_model.bus_map.set_adapter(self.adapter)

        # Connect SDT sequencers to virtual sequencer
        self.virtual_sequencer.apb_seqr = self.apb_agent.sequencer
        self.virtual_sequencer.cif_seqrs = [a.sequencer for a in self.sdt_cif_agents]
        self.virtual_sequencer.mif_seqr = self.sdt_mif_agent.sequencer

        self.logger.info("End connect_phase() -> MARB env")
