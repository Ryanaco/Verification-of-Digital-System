# cl_reg_block.py
from pyuvm import uvm_reg_block, uvm_reg_map
from .cl_ctrl_reg import cl_ctrl_reg
from .cl_dprio_reg import cl_dprio_reg


class cl_reg_block(uvm_reg_block):
    """
    目标：
      - ctrl_reg 最终地址  0x000
      - dprio_reg 最终地址 0x100
    做法：
      - 用 configure(self, address, hdl_path="") 给每个 reg 设“内部地址”
      - map 基址设 0x0；reg 自己带偏移地址
    """

    def __init__(self, name="reg_block"):
        super().__init__(name)
        self.bus_map = None
        self.ctrl_reg = None
        self.dprio_reg = None
        self._built = False

    def build(self):
        if self._built:
            return
        self._built = True

        # 1) 实例化并配置寄存器
        self.ctrl_reg = cl_ctrl_reg("ctrl_reg")
        self.ctrl_reg.configure(self, "0x0", "")
        self.ctrl_reg.build()

        self.dprio_reg = cl_dprio_reg("dprio_reg")
        self.dprio_reg.configure(self, "0x100", "")
        self.dprio_reg.build()

        # 2) 创建并配置 bus_map（注意 pyuvm 只接收 parent, base_addr）
        self.bus_map = uvm_reg_map("bus_map")
        self.bus_map.configure(self, "0x0")

        # 3) 把寄存器加入 map（偏移地址用 16 进制字符串）
        self.bus_map.add_reg(self.ctrl_reg, "0x0", "RW")
        self.bus_map.add_reg(self.dprio_reg, "0x0", "RW")

        # 4) 设置默认 map（pyuvm 推荐这样做）
        self.default_map = self.bus_map

        # 5) 调试输出
        try:
            print(f"[DEBUG] ctrl_reg bits = {self.ctrl_reg.get_n_bits()}")
            print(f"[DEBUG] dprio_reg bits = {self.dprio_reg.get_n_bits()}")
            print(f"[DEBUG] ctrl_reg addr = {self.ctrl_reg.get_address()}")
            print(f"[DEBUG] dprio_reg addr = {self.dprio_reg.get_address()}")
        except Exception:
            pass
