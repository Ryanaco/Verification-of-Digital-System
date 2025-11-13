from pyuvm.s21_uvm_reg_map import *


class uvm_reg_map_always_predict(uvm_reg_map):
    """
    扩展 uvm_reg_map：
    - 移除了 enable_auto_predict 限制，总是调用 predictor
    - 自动兼容整数和字符串类型的地址 (例如 0x4 与 "0x4")
    - 增加详细日志，方便调试寄存器映射
    """

    def __init__(self, name="uvm_reg_map_always_predict"):
        super().__init__(name)

    # ==============================================================
    # 🧠 辅助函数：自动解析寄存器 key
    # ==============================================================
    def _resolve_reg_key(self, reg_address):

            # 1️⃣ 完全匹配
            if reg_address in self._regs:
                return reg_address

            # 2️⃣ 忽略大小写匹配
            if isinstance(reg_address, str):
                for key in self._regs.keys():
                    if key.lower() == reg_address.lower():
                        return key

            # 3️⃣ 整数形式匹配
            if isinstance(reg_address, int):
                for key in self._regs.keys():
                    try:
                        if int(key, 16) == reg_address:
                            return key
                    except Exception:
                        pass

            # 4️⃣ 字符串转整数再匹配整数 key
            if isinstance(reg_address, str):
                try:
                    addr_int = int(reg_address, 16)
                    for key in self._regs.keys():
                        if isinstance(key, int) and key == addr_int:
                            return key
                except ValueError:
                    pass

            # 5️⃣ 打印现有寄存器映射方便 debug
            print(f"[DEBUG] Available reg keys in map: {list(self._regs.keys())}")
            raise RuntimeError(f"[uvm_reg_map_always_predict] Unknown reg address: {reg_address}")



    # ==============================================================
    # 📖 READ
    # ==============================================================
    async def process_read_operation(self, reg_address, path: path_t, check: check_t):
        local_adapter = self.get_adapter()
        item = uvm_reg_item()
        item.set_kind(access_e.UVM_READ)
        item.set_door(path)
        item.set_map(self)
        item.set_parent_sequence(None)

        self.check_process_integrity(local_adapter, item)
        local_sequencer = self.get_sequencer()

        # Resolve key safely
        key = self._resolve_reg_key(reg_address)

        if path is path_t.BACKDOOR:
            uvm_not_implemeneted(self.header, "BACKDOOR not implemented")
        elif path is path_t.USER_FRONTDOOR:
            uvm_not_implemeneted(self.header, "USER_FRONTDOOR not implemented")
        elif path is path_t.FRONTDOOR:
            local_bus_op = uvm_reg_bus_op()
            local_bus_op.kind = access_e.UVM_READ
            local_bus_op.addr = reg_address
            local_bus_op.n_bits = self._regs[key].get_reg_size()
            local_bus_op.byte_en = local_adapter.get_byte_en()

            # Build and start sequence
            local_adapter.set_item(item)
            bus_req = local_adapter.reg2bus(local_bus_op)
            local_adapter.set_item(None)
            local_sequence = local_adapter.get_parent_sequence()
            local_sequence.sequencer = local_sequencer

            self.logger.debug(f"[MAP] READ start @ addr={reg_address} key={key}")
            await local_sequence.start_item(bus_req)
            await local_sequence.finish_item(bus_req)
            local_adapter.bus2reg(bus_req, local_bus_op)

            # Always predict
            local_predictor = self.get_predictor()
            local_predictor.predict(local_bus_op, check)
            self.logger.debug(f"[MAP] READ done -> data=0x{local_bus_op.data:X}")

            return local_bus_op.status, local_bus_op.data

    # ==============================================================
    # ✍️ WRITE
    # ==============================================================
    async def process_write_operation(self, reg_address, data_to_be_written,
                                      path: path_t, check: check_t):
        local_adapter = self.get_adapter()
        item = uvm_reg_item()
        item.set_kind(access_e.UVM_WRITE)
        item.set_value(data_to_be_written)
        item.set_door(path)
        item.set_map(self)
        item.set_parent_sequence(None)

        self.check_process_integrity(local_adapter, item)
        local_sequencer = self.get_sequencer()

        # Resolve key safely
        key = self._resolve_reg_key(reg_address)

        if path is path_t.BACKDOOR:
            uvm_not_implemeneted(self.header, "BACKDOOR not implemented")
        elif path is path_t.USER_FRONTDOOR:
            uvm_not_implemeneted(self.header, "USER_FRONTDOOR not implemented")
        elif path is path_t.FRONTDOOR:
            local_bus_op = uvm_reg_bus_op()
            local_bus_op.kind = access_e.UVM_WRITE
            local_bus_op.addr = reg_address
            local_bus_op.n_bits = self._regs[key].get_reg_size()
            local_bus_op.byte_en = local_adapter.get_byte_en()
            local_bus_op.data = data_to_be_written

            # Build and start sequence
            local_adapter.set_item(item)
            bus_req = local_adapter.reg2bus(local_bus_op)
            local_adapter.set_item(None)
            local_sequence = local_adapter.get_parent_sequence()
            local_sequence.sequencer = local_sequencer

            self.logger.debug(f"[MAP] WRITE start @ addr={reg_address} key={key} data=0x{data_to_be_written:X}")
            await local_sequence.start_item(bus_req)
            await local_sequence.finish_item(bus_req)
            local_adapter.bus2reg(bus_req, local_bus_op)

            # Always predict
            local_predictor = self.get_predictor()
            local_predictor.predict(local_bus_op, check)
            self.logger.debug("[MAP] WRITE done (prediction triggered)")

            return local_bus_op.status

    # ==============================================================
    # Predictor Getter
    # ==============================================================
    def get_predictor(self):
        if self.predictor is None:
            uvm_error(self.header, "Predictor not set in map")
        return self.predictor
