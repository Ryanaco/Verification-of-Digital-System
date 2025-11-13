///////////////////////////////////////////////////////////////////////////////
//// APB interface for configuring the behaviour of the memory arbiter
///////////////////////////////////////////////////////////////////////////////
module apb_ctrl #(
  parameter MEM_ARB_CLIENTS_P = 3 // Number of client interfaces of the arbiter
)
(
  input logic clk,
  input logic rst,

  // APB interface signals
  input   logic          conf_wr,
  input   logic          conf_sel,
  input   logic          conf_enable,
  input   logic [32-1:0] conf_addr,
  input   logic [32-1:0] conf_wdata,
  input   logic [ 4-1:0] conf_strb,
  output  logic [32-1:0] conf_rdata,
  output  logic          conf_ready,
  output  logic          conf_slverr,

  // ctrl register
  output ctrl_reg_t ctrl,

  // Icarus workaround, all dprio registers separatly, always multiple of 4
  output dprio_reg_t dprio0,
  output dprio_reg_t dprio1,
  output dprio_reg_t dprio2,
  output dprio_reg_t dprio3,

  // One wstrb per client, but it has to be a multiple of 4
  output logic [((((MEM_ARB_CLIENTS_P-1)/4)+1)*4)-1:0] dprio_wstrb
);

  // Number of 32bit registers to hold all clients
  localparam NUM_DPRIO_32b_REG_P = ((MEM_ARB_CLIENTS_P-1)/4)+1;

  // Number of available client dprio registers. Is always multiple of 4
  localparam NUM_DPRIO_CLIENTS_MULTIPLE_OF_FOUR = NUM_DPRIO_32b_REG_P*4;

  states_t apb_state;

  ctrl_reg_t  next_ctrl;
  dprio_reg_t next_dprio [NUM_DPRIO_CLIENTS_MULTIPLE_OF_FOUR];

  logic [31:0]                                   next_rdata, rdata;
  logic                                          next_ready, next_slverr;
  logic [NUM_DPRIO_CLIENTS_MULTIPLE_OF_FOUR-1:0] next_dprio_wstrb;

  // Assign dprio registers to dprio register array
  dprio_reg_t dprio [((((MEM_ARB_CLIENTS_P-1)/4)+1)*4)];

  assign dprio0 = dprio[0];
  assign dprio1 = dprio[1];
  assign dprio2 = dprio[2];
  assign dprio3 = dprio[3];


///////////////////////////////////////////////////////////////////////////////
//// Registers
///////////////////////////////////////////////////////////////////////////////
//-------------------------------------------------
// Registers for ctrl, dprio and dprio_wstrb
//-------------------------------------------------
  always_ff @ (posedge clk, posedge rst) begin
    if (rst) begin
      ctrl          <= '0;
      for (int i = 0; i < NUM_DPRIO_CLIENTS_MULTIPLE_OF_FOUR; i++) begin
        dprio[i]    <= '0;
      end
      dprio_wstrb   <= '0;
    end else begin
      ctrl          <= next_ctrl;
      dprio[0]      <= next_dprio[0];
      dprio[1]      <= next_dprio[1];
      dprio[2]      <= next_dprio[2];
      dprio[3]      <= next_dprio[3];
      dprio_wstrb   <= next_dprio_wstrb;
    end
  end
//-------------------------------------------------
// Register for APB interface
//-------------------------------------------------
  always_ff @ (posedge clk, posedge rst) begin
    if (rst) begin
      conf_ready    <= 0;
      conf_rdata    <= 0;
      conf_slverr   <= 0;
    end else begin
      conf_ready    <= next_ready;
      conf_rdata    <= next_rdata;
      conf_slverr   <= next_slverr;
    end
  end

///////////////////////////////////////////////////////////////////////////////
//// APB State Machine
///////////////////////////////////////////////////////////////////////////////
//-------------------------------------------------
// Register for APB state machine including next state logic
//-------------------------------------------------
  always_ff @ (posedge clk, posedge rst) begin
    if (rst) begin
      apb_state             <= STATES_IDLE;
    end else begin
      case (apb_state)
        STATES_IDLE: begin
          if (conf_sel) begin        // APB Master requests access
            apb_state       <= STATES_ACCESS;
          end
        end
        STATES_ACCESS:  apb_state  <= STATES_IDLE;  // Only stay in access state for one cycle
        default: apb_state  <= STATES_IDLE;
      endcase
    end
  end
//-------------------------------------------------
// APB state decoding
//-------------------------------------------------
  always_comb begin
    next_rdata        = conf_rdata;
    next_ready        = 0;
    next_slverr       = 0;

    // next_dprio        = dprio;
    next_dprio[0]     = dprio[0];
    next_dprio[1]     = dprio[1];
    next_dprio[2]     = dprio[2];
    next_dprio[3]     = dprio[3];

    next_ctrl         = ctrl;
    next_dprio_wstrb  = 0;

    case (apb_state)
      STATES_IDLE: begin
        next_rdata    = 0;
        next_slverr   = 0;
        if (conf_sel) begin     // Master wants to initiate an access
          next_ready  = 1;      // Signals that we can complete the transfer by next rising clock (remember next_ is delayed one cycle)
          if (conf_wr) begin    // Write access
            if (conf_addr == MEM_ARBITER_CTRL_REG_ADDR) begin
              // Checking for sparse transfers
              next_ctrl[ 7: 0]  = (conf_strb[0] == 1'b1 ) ? conf_wdata[ 7: 0] : ctrl[ 7: 0];
              next_ctrl[15: 8]  = (conf_strb[1] == 1'b1 ) ? conf_wdata[15: 8] : ctrl[15: 8];
              next_ctrl[23:16]  = (conf_strb[2] == 1'b1 ) ? conf_wdata[23:16] : ctrl[23:16];
              next_ctrl[31:24]  = (conf_strb[3] == 1'b1 ) ? conf_wdata[31:24] : ctrl[31:24];
            end
            for (int i = 0; i < NUM_DPRIO_32b_REG_P; i++) begin
              if (conf_addr == (MEM_ARBITER_DPRIO_REG_BASE_ADDR +4*i)) begin
                // Checking for sparse transfers
                next_dprio[i]   = (conf_strb[0] == 1'b1 ) ? conf_wdata[ 7: 0] : dprio[i];
                next_dprio[i+1] = (conf_strb[1] == 1'b1 ) ? conf_wdata[15: 8] : dprio[i+1];
                next_dprio[i+2] = (conf_strb[2] == 1'b1 ) ? conf_wdata[23:16] : dprio[i+2];
                next_dprio[i+3] = (conf_strb[3] == 1'b1 ) ? conf_wdata[31:24] : dprio[i+3];
                // Connecting strobe signal
                next_dprio_wstrb[4*i +: 4] = conf_strb;
              end
            end
          end else begin      // Read access
            if (conf_addr == MEM_ARBITER_CTRL_REG_ADDR) begin
              next_rdata    = ctrl;    // Prepare ctrl data for read access
            end
            for (int i = 0; i < NUM_DPRIO_32b_REG_P; i++) begin
              if (conf_addr == (MEM_ARBITER_DPRIO_REG_BASE_ADDR + 4*i)) begin
                next_rdata  = { dprio[i+3], dprio[i+2], dprio[i+1], dprio[i] };   // Prepare dprio data for read access
              end
            end
          end //rd
        end // sel
      end
      STATES_ACCESS: begin
        ;         // Use the default assignments
      end
      default: ;  // apb_state out of known states
    endcase       // case (apb_state)
  end
endmodule
