
`timescale 1ns/1ps

module mux(
    input                       clk,
    input logic unsigned [3:0]  A,
    input logic unsigned [1:0]  sel,
    output logic unsigned       out
);

    always @(posedge clk) begin
       out <= A[sel];
    end
       
endmodule
