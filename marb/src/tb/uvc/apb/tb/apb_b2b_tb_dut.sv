module toplevel #(
    parameter ADDR_WIDTH = 32,         // APB addr width
    parameter DATA_WIDTH = 32          // APB data width
  )
  (
    input  logic                      clk,
    input  logic                      rst,
    input  logic                      wr,
    input  logic                      sel,
    input  logic                      enable,
    input  logic [ADDR_WIDTH-1:0]     addr,
    input  logic [DATA_WIDTH-1:0]     wdata,
    input  logic [DATA_WIDTH/8-1:0]   strb,
    output logic [DATA_WIDTH-1:0]     rdata,
    output logic                      ready,
    output logic                      slverr
  );

    initial begin
        $dumpfile ("sim_build/apb_b2b_waves.vcd");
        $dumpvars (0, toplevel);
    end

endmodule