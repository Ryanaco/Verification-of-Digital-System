////////////////////////////////////////////////////////////////////////////////////////////////////////////
// Saturation Filter TB
//
//  - TB module wrapping the design.
//
/////////////////////////////////////////////////////////////////////////////////////////////////////////////

// Includes are defined in Makefile when using COCOTB
`ifndef COCOTB_SIM
  `include "summer.sv"
`endif

module summer_wrapper #(
    parameter DATA_W = 4       // Data signal bit size
  )
  (
    input   logic               clk,
    input   logic               rst,
    input   logic               in_valid,   // input data valid signal
    input   logic [DATA_W-1:0]  in_data,    // input data signal
    output  logic               out_valid,  // valid output signal
    output  logic [DATA_W-1:0]  out_data    // output signal
  );

  summer #(
    .DATA_W(DATA_W)
  )
  summer_i (
    .clk(clk),
    .rst(rst),
    .in_valid(in_valid),
    .in_data(in_data),
    .out_valid(out_valid),
    .out_data(out_data)
  );

endmodule: summer_wrapper