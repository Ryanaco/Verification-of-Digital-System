module mem_arb_wrapper
#(
  parameter
    MEM_ARB_CLIENTS_P = 3,                      // Number of client interfaces of the arbiter
    ADDR_WIDTH = 8,
    DATA_WIDTH = 8,
    CLOCK_WIDTH = 1,
    RESET_WIDTH = 1
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
    mem_arb #(
    .MEM_ARB_CLIENTS_P(MEM_ARB_CLIENTS_P),
    .ADDR_WIDTH(ADDR_WIDTH),
    .DATA_WIDTH(DATA_WIDTH)
    )mem_arb_i(
      .clk(clk),
      .stable(stable),
      .rst(rst),

      // APB inteface signals
      .conf_wr(conf_wr),
      .conf_sel(conf_sel),
      .conf_enable(conf_enable),
      .conf_addr(conf_addr),
      .conf_wdata(conf_wdata),
      .conf_strb(conf_strb),
      .conf_rdata(conf_rdata),
      .conf_ready(conf_ready),
      .conf_slverr(conf_slverr),

      // 3 client SDT interface signals
      .c0_rd(c0_rd),
      .c0_wr(c0_wr),
      .c0_addr(c0_addr),
      .c0_wr_data(c0_wr_data),
      .c0_rd_data(c0_rd_data),
      .c0_ack(c0_ack),

      .c1_rd(c1_rd),
      .c1_wr(c1_wr),
      .c1_addr(c1_addr),
      .c1_wr_data(c1_wr_data),
      .c1_rd_data(c1_rd_data),
      .c1_ack(c1_ack),

      .c2_rd(c2_rd),
      .c2_wr(c2_wr),
      .c2_addr(c2_addr),
      .c2_wr_data(c2_wr_data),
      .c2_rd_data(c2_rd_data),
      .c2_ack(c2_ack),


      // Memory STD interface signals
      .m_rd(m_rd),
      .m_wr(m_wr),
      .m_addr(m_addr),
      .m_wr_data(m_wr_data),
      .m_rd_data(m_rd_data),
      .m_ack

    );

endmodule
