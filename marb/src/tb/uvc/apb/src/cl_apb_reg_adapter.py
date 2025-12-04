from pyuvm import *
from . import apb_common
from .cl_apb_seq_item import cl_apb_seq_item


# ✅ 定义兼容性封装（PyUVM 1.9 没有 uvm_report_info，也没有 UVM_LOW）
def uvm_report_info(tag, msg, verbosity=None):
    """统一日志接口封装（兼容旧式 UVM）"""
    try:
        uvm_root().logger.info(f"[{tag}] {msg}")
    except Exception:
        print(f"[INFO][{tag}] {msg}")

def uvm_report_error(tag, msg):
    """统一错误接口封装"""
    try:
        uvm_root().logger.error(f"[{tag}] {msg}")
    except Exception:
        print(f"[ERROR][{tag}] {msg}")


class cl_apb_reg_adapter(uvm_reg_adapter):
    """
    APB Register Adapter for PyUVM.
    Converts between UVM register transactions and APB sequence items,
    and bridges register model read/write operations to the APB agent.
    """

    def __init__(self, name="cl_apb_reg_adapter"):
        super().__init__(name)
        self.supports_byte_enable = False
        self.provides_responses = True

    # -------------------------------------------------------------------------
    # Register model ↔ Bus interface conversion
    # -------------------------------------------------------------------------
    def reg2bus(self, rw):
        apb = cl_apb_seq_item.create("apb_item")

        if rw.kind == access_e.UVM_READ:
            apb.op = apb_common.OpType.RD
        elif rw.kind == access_e.UVM_WRITE:
            apb.op = apb_common.OpType.WR

        apb.addr = int(rw.addr.replace("0x", ""), 16) if isinstance(rw.addr, str) else int(rw.addr)
        apb.data = rw.data
        return apb

    def bus2reg(self, bus_item, rw):
        assert isinstance(bus_item, cl_apb_seq_item), "Bus item is not of type cl_apb_seq_item"
        apb = bus_item

        rw.kind = access_e.UVM_READ if apb.op == apb_common.OpType.RD else access_e.UVM_WRITE
        rw.addr = apb.addr
        rw.data = apb.data
        rw.status = status_t.IS_OK if getattr(apb, "slverr", 0) == 0 else status_t.IS_NOT_OK

    # -------------------------------------------------------------------------
    # Async register map access functions (pyuvm entrypoints)
    # -------------------------------------------------------------------------
    async def process_write_operation(self, map, address, data, byte_en=None, parent=None):
        """Perform a register write using the APB sequencer"""
        if isinstance(address, uvm_reg_map):
            address, data = data, byte_en

        try:
            uvm_top = uvm_root()
            test_top = uvm_top.get_child("uvm_test_top")
            env = test_top.get_child("marb_tb_env") if test_top else None
            seqr = env.apb_agent.sequencer if env else None
            if seqr is None:
                raise RuntimeError("❌ APB sequencer not found in environment")

            txn = cl_apb_seq_item.create("wr_txn")
            txn.op = apb_common.OpType.WR
            txn.addr = int(address)
            txn.data = data

            uvm_report_info("APB_ADAPTER", f"📝 Write txn -> addr=0x{txn.addr:X}, data=0x{txn.data:X}")
            await seqr.start_item(txn)
            await seqr.finish_item(txn)
            uvm_report_info("APB_ADAPTER", "✅ Write transaction completed")

            return status_t.IS_OK

        except Exception as e:
            uvm_report_error("APB_ADAPTER", f"❌ Exception in write operation: {e}")
            return status_t.IS_NOT_OK

    async def process_read_operation(self, map, address, byte_en=None, parent=None):
        """Perform a register read using the APB sequencer"""
        if isinstance(address, uvm_reg_map):
            address = byte_en

        try:
            uvm_top = uvm_root()
            test_top = uvm_top.get_child("uvm_test_top")
            env = test_top.get_child("marb_tb_env") if test_top else None
            seqr = env.apb_agent.sequencer if env else None
            if seqr is None:
                raise RuntimeError("❌ APB sequencer not found in environment")

            txn = cl_apb_seq_item.create("rd_txn")
            txn.op = apb_common.OpType.RD
            txn.addr = int(address)

            uvm_report_info("APB_ADAPTER", f"🔍 Read txn -> addr=0x{txn.addr:X}")
            await seqr.start_item(txn)
            await seqr.finish_item(txn)

            rd_val = getattr(txn, "data", 0)
            uvm_report_info("APB_ADAPTER", f"📥 Read result <- addr=0x{txn.addr:X}, data=0x{rd_val:X}")

            return (status_t.IS_OK, rd_val)

        except Exception as e:
            uvm_report_error("APB_ADAPTER", f"❌ Exception in read operation: {e}")
            return (status_t.IS_NOT_OK, 0)
