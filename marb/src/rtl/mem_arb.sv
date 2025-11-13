///////////////////////////////////////////////////////////////////////////////
//// Memory arbiter with dynamic and fixed priority modes
///////////////////////////////////////////////////////////////////////////////

module mem_arb
#(
  parameter
  MEM_ARB_CLIENTS_P = 3,                      // Number of client interfaces of the arbiter
  ADDR_WIDTH = 8,
  DATA_WIDTH = 8
)
(
  input   logic       clk,
  input   logic       stable,
  input   logic       rst,

  // APB inteface signals
  input   logic          conf_wr,
  input   logic          conf_sel,
  input   logic          conf_enable,
  input   logic [32-1:0] conf_addr,
  input   logic [32-1:0] conf_wdata,
  input   logic [ 4-1:0] conf_strb,
  output  logic [32-1:0] conf_rdata,
  output  logic          conf_ready,
  output  logic          conf_slverr,

  // 3 client SDT interface signals
  input   logic                  c0_rd,
  input   logic                  c0_wr,
  input   logic [ADDR_WIDTH-1:0] c0_addr,
  input   logic [DATA_WIDTH-1:0] c0_wr_data,
  output  logic [DATA_WIDTH-1:0] c0_rd_data,
  output  logic                  c0_ack,

  input   logic                  c1_rd,
  input   logic                  c1_wr,
  input   logic [ADDR_WIDTH-1:0] c1_addr,
  input   logic [DATA_WIDTH-1:0] c1_wr_data,
  output  logic [DATA_WIDTH-1:0] c1_rd_data,
  output  logic                  c1_ack,

  input   logic                  c2_rd,
  input   logic                  c2_wr,
  input   logic [ADDR_WIDTH-1:0] c2_addr,
  input   logic [DATA_WIDTH-1:0] c2_wr_data,
  output  logic [DATA_WIDTH-1:0] c2_rd_data,
  output  logic                  c2_ack,


  // Memory STD interface signals
  output  logic                  m_rd,
  output  logic                  m_wr,
  output  logic [ADDR_WIDTH-1:0] m_addr,
  output  logic [DATA_WIDTH-1:0] m_wr_data,
  input   logic [DATA_WIDTH-1:0] m_rd_data,
  input   logic                   m_ack

);

  localparam CLIENTS_BWIDTH_P                   = $clog2(MEM_ARB_CLIENTS_P);    // Bit width to represent all clients
  localparam NUM_DPRIO_32b_REG_P                = ((MEM_ARB_CLIENTS_P-1)/4)+1;  // Number of 32bit registers to hold all clients
  localparam NUM_DPRIO_CLIENTS_MULTIPLE_OF_FOUR = NUM_DPRIO_32b_REG_P*4;        // Number of available client dprio registers. Is always multiple of 4

  states_t                            state;

  ctrl_reg_t      ctrl_reg;
  dprio_reg_t     dprio_reg       [NUM_DPRIO_CLIENTS_MULTIPLE_OF_FOUR]; // Multiply by 4 to get number of 8-bit regs alligned by 32bit groups

  logic [CLIENTS_BWIDTH_P-1:0]        priority_list   [MEM_ARB_CLIENTS_P];
  logic [CLIENTS_BWIDTH_P-1:0]        cif_select;

  logic [NUM_DPRIO_32b_REG_P*4-1:0]   dprio_wstrb;  // Write strobe signals // Multiply by 4, to get one bit pr dprio_reg, and group every 4 bits.
  logic                               dprio_wstrb_single;

  // Local client interface signals
  logic [MEM_ARB_CLIENTS_P-1:0][1:0]  cif_req;
  logic [31:0]                        cif_addr        [MEM_ARB_CLIENTS_P];
  logic [31:0]                        cif_wr_data     [MEM_ARB_CLIENTS_P];
  logic [31:0]                        cif_rd_data     [MEM_ARB_CLIENTS_P];
  logic                               cif_ack         [MEM_ARB_CLIENTS_P];
  logic [CLIENTS_BWIDTH_P-1:0]        cif_select_list [MEM_ARB_CLIENTS_P];

  // Signals for generating waveforms
  logic [1:0] prio_list0;
  logic [1:0] prio_list1;
  logic [1:0] prio_list2;

///////////////////////////////////////////////////////////////////////////////
//// Module Instantiations
///////////////////////////////////////////////////////////////////////////////

//-------------------------------------------------
// APB module instanciation
//-------------------------------------------------
  apb_ctrl #(
    .MEM_ARB_CLIENTS_P(MEM_ARB_CLIENTS_P)
  ) apb_ctrl_i (
    .clk(clk),
    .rst(rst),
    .conf_wr(conf_wr),
    .conf_sel(conf_sel),
    .conf_enable(conf_enable),
    .conf_addr(conf_addr),
    .conf_wdata(conf_wdata),
    .conf_strb(conf_strb),
    .conf_rdata(conf_rdata),
    .conf_ready(conf_ready),
    .conf_slverr(conf_slverr),
    .ctrl(ctrl_reg),
    // Icarus workaround, separate signals
    .dprio0(dprio_reg[0]),
    .dprio1(dprio_reg[1]),
    .dprio2(dprio_reg[2]),
    .dprio3(dprio_reg[3]),
    .dprio_wstrb(dprio_wstrb)
  );

//-------------------------------------------------
// priority_sel module instanciation
//-------------------------------------------------
  priority_sel #(
    .MEM_ARB_CLIENTS_P(MEM_ARB_CLIENTS_P)
  ) priority_sel_i (
    .clk(clk),
    .rst(rst),
    .ctrl(ctrl_reg),
    .dprio(dprio_reg),
    .dprio_wstrb(dprio_wstrb_single),
    // Icarus workaround, separate signals
    .prio_list0(priority_list[0]),
    .prio_list1(priority_list[1]),
    .prio_list2(priority_list[2])
  );

///////////////////////////////////////////////////////////////////////////////
//// Assignments
///////////////////////////////////////////////////////////////////////////////
//-------------------------------------------------
// Combine all write strobes into one logic signal
// Since we don't care which strobes are asserted
// only the case if any of them is asserted.
//-------------------------------------------------
  assign dprio_wstrb_single = |dprio_wstrb; // Signal for module priority selection only cares if any of the strobes are active, not which ones.
//-------------------------------------------------
// Connect all client interfaces to local logic, for easier manipulation
//-------------------------------------------------
  assign cif_req[0]       = {c0_rd, c0_wr};
  assign cif_addr[0]      = c0_addr;
  assign cif_wr_data[0]   = c0_wr_data;
  assign c0_rd_data       = cif_rd_data[0];
  assign c0_ack           = cif_ack[0];

  assign cif_req[1]       = {c1_rd, c1_wr};
  assign cif_addr[1]      = c1_addr;
  assign cif_wr_data[1]   = c1_wr_data;
  assign c1_rd_data       = cif_rd_data[1];
  assign c1_ack           = cif_ack[1];

  assign cif_req[2]       = {c2_rd, c2_wr};
  assign cif_addr[2]      = c2_addr;
  assign cif_wr_data[2]   = c2_wr_data;
  assign c2_rd_data       = cif_rd_data[2];
  assign c2_ack           = cif_ack[2];

//-------------------------------------------------
// cif_select_list is a vector of all clients that
// requests access to the memory sorted by their priorty
//
// cif_select_list[0] will always hold the ID of the client
// who has the highest priority and requests access.
//
// If no client have requested access, the vector
// will be all zeroes, meaning that when no one wants
// access the arbiter will check client0 at every cycle
// until any client request access.
//-------------------------------------------------
  genvar i;
  generate
    for (i = 0; i < MEM_ARB_CLIENTS_P-1; i++) begin
      assign cif_select_list[i]               = ( cif_req[priority_list[i]] > 0 ) ? priority_list[i] : cif_select_list[i+1];
    end
  endgenerate
  // The last entry requires a special case because it handles the last entry in priority_list
  assign cif_select_list[MEM_ARB_CLIENTS_P-1] = ( cif_req[priority_list[MEM_ARB_CLIENTS_P-1]] > 0 ) ? priority_list[MEM_ARB_CLIENTS_P-1] : '0;

///////////////////////////////////////////////////////////////////////////////
//// Registers
///////////////////////////////////////////////////////////////////////////////
//-------------------------------------------------
// cif_select register
//-------------------------------------------------
  always_ff @ (posedge clk, posedge rst) begin
    if (rst) begin
      cif_select    <= '0;
    end else begin
      if (state==STATES_IDLE) begin      // Only update selected client interface when we are in IDLE state, otherwise we might end up signaling the wrong interface
        cif_select  <= cif_select_list[0];
      end
    end
    // Assigning values for waveform
    prio_list0 <= priority_list[0];
    prio_list1 <= priority_list[1];
    prio_list2 <= priority_list[2];
  end
//-------------------------------------------------
// Memory arbiter State machine
//
// Selects the next state of the SM, based on current state and current inputs
//-------------------------------------------------
  always_ff @ (posedge clk, posedge rst) begin
    if (rst) begin
      state         <= STATES_IDLE;
    end else begin
      case (state)
        STATES_IDLE: begin
          if ( |cif_req && !m_ack && ctrl_reg.en) begin   // Arbiter has to be enabled, mif is ready, and at least one client wants access.
            state   <= STATES_ACCESS;
          end
        end
        STATES_ACCESS: begin
          if (m_ack) begin    // When memory ack, switch to IDLE state
            state   <= STATES_IDLE;
          end
        end
        default: begin
          state     <= STATES_IDLE;
        end
      endcase
    end
  end

///////////////////////////////////////////////////////////////////////////////
//// Logic
///////////////////////////////////////////////////////////////////////////////
//-------------------------------------------------
// Memory arbiter State decoding
//
// Sets the outputs of the state machine according to the current state
//-------------------------------------------------
  always_comb begin
    m_rd                            = 1'b0;
    m_wr                            = 1'b0;
    m_addr                          = '0;
    m_wr_data                       = '0;
    for (int i = 0 ; i < MEM_ARB_CLIENTS_P ; i++ ) begin
      cif_ack[i]                      = 1'b0;
      cif_rd_data[i]                  = '0;
    end
    case (state)
      STATES_IDLE: ;                         // Wait for a client to request access
      STATES_ACCESS: begin                   // ACCESS state - Connect the desired client to the mif
        m_addr                      = cif_addr[cif_select];
        cif_ack[cif_select]         = m_ack;
        if ( (cif_req[cif_select] & 2'b01) == 2'b01) begin   // Write access
          m_wr                      = 1'b1;
          m_wr_data                 = cif_wr_data[cif_select];
        end else begin                    // Read access
          m_rd                      = 1'b1;
          if (m_ack)
            cif_rd_data[cif_select] = m_rd_data;          // When mif signals ack, we connect rd_data
          else
            cif_rd_data[cif_select] = '0;
        end
      end
      default: m_addr               = '0;
    endcase
  end

// Generate output waveforms
  initial begin
    $dumpfile ("sim_build/mem_arb_waves.vcd");
    $dumpvars (0, mem_arb);
  end

endmodule
