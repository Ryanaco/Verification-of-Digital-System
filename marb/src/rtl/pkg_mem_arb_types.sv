///////////////////////////////////////////////////////////////////////////////
//// Package containing states and register types used in Memory Arbiter
///////////////////////////////////////////////////////////////////////////////

typedef struct packed {
  logic [28:0]  unused;
  logic [1:0]   mode;
  logic en;
} ctrl_reg_t;

typedef struct packed {
  logic [7:0]   cif;
} dprio_reg_t;

typedef enum {
  STATES_IDLE,
  STATES_ACCESS
} states_t;

typedef enum {
  SORTER_IDLE,
  SORTER_CLEAR,
  SORTER_SORT
} sorter_states_t;

parameter MEM_ARBITER_CTRL_REG_ADDR       = 32'h0000_0000;
parameter MEM_ARBITER_DPRIO_REG_BASE_ADDR = 32'h0000_0004;