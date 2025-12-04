from pyuvm import *


class cl_ctrl_reg(uvm_reg):
    def __init__(self, name="cl_ctrl_reg", reg_width=32):
        super().__init__(name, reg_width)
        # 定义字段
        self.F_en = uvm_reg_field("en")
        self.F_mode = uvm_reg_field("mode")
        self.F_unused = uvm_reg_field("unused")
        self._built = False  # 防止重复构建

    def build(self):
        if self._built:
            return
        self._built = True

        # pyuvm 的 configure 原型为：
        # configure(parent, size, lsb_pos, access, reset, has_reset)
        # 没有 is_volatile
        self.F_en.configure(self, 1, 0, "RW", 0, True)
        self.F_mode.configure(self, 2, 1, "RW", 0, True)
        self.F_unused.configure(self, 29, 3, "RW", 0, True)

        # 锁定字段配置并设定预测模式
        self._set_lock()
        self.set_prediction(predict_t.PREDICT_DIRECT)
