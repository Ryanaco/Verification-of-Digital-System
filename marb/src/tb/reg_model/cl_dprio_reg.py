from pyuvm import *


class cl_dprio_reg(uvm_reg):
    def __init__(self, name="cl_dprio_reg", reg_width=32):
        super().__init__(name, reg_width)
        self.F_cif0 = uvm_reg_field("cif0")
        self.F_cif1 = uvm_reg_field("cif1")
        self.F_cif2 = uvm_reg_field("cif2")
        self.F_extra = uvm_reg_field("extra")
        self._built = False

    def build(self):
        if self._built:
            return
        self._built = True

        self.F_cif0.configure(self, 8, 0, "RW", 0, True)
        self.F_cif1.configure(self, 8, 8, "RW", 0, True)
        self.F_cif2.configure(self, 8, 16, "RW", 0, True)
        self.F_extra.configure(self, 8, 24, "RW", 0, True)

        self._set_lock()
        self.set_prediction(predict_t.PREDICT_DIRECT)
