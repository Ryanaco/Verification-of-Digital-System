from pyuvm.s26_uvm_predictor import uvm_reg_predictor
from pyuvm.s21_uvm_reg_map import uvm_reg_map
from pyuvm.s24_uvm_reg_includes import check_t, uvm_error, access_e

class cl_reg_predictor(uvm_reg_predictor):
    def __init__(self,  name="cl_reg_predictor"):
        super().__init__(name)
        self.header = name + " -- "

    def configure(self, map):
        if isinstance(map,uvm_reg_map):
            self.map = map
        else:
            uvm_error(self.header,f"configure -- map has to be of type {type(uvm_reg_map)} is of type {type(map)}" )

    def predict(self,bus_op,check):
        if check == check_t.NO_CHECK:
            reg = self.map.get_reg_by_offset(hex(bus_op.addr))
            if bus_op.kind == access_e.UVM_WRITE:
                reg.predict(bus_op.data,bus_op.kind)
