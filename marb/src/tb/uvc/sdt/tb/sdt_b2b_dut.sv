/**
////////////////////////////////////////////////////////////////////////////////////////////////////////////

- Dummy SDT module to be used for the B2B test.

/////////////////////////////////////////////////////////////////////////////////////////////////////////////
*/

module sdt_b2b #(
    parameter ADDR_WIDTH = 8,
    parameter DATA_WIDTH = 8
  )
  (
    input  logic clk,
    input  logic rst,
    input  logic rd,
    input  logic wr,
    input  logic [ADDR_WIDTH-1:0] addr,
    input  logic [DATA_WIDTH-1:0] wr_data,
    output logic [DATA_WIDTH-1:0] rd_data,
    output logic ack
  );


    initial begin
        $dumpfile ("sim_build/sdt_b2b_waves.vcd");
        $dumpvars (0, sdt_b2b);
    end

endmodule