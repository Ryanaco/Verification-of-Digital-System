
`timescale 1ns/1ps

module parallel(
    input                       clk,
    input logic unsigned [3:0]  A,
    input logic unsigned [3:0]  B,
    input logic unsigned [3:0]  C,
    output logic unsigned [1:0] out
);

    always @(posedge clk) begin
        if (A == B) begin
            out <= 1;
        end if (A == C) begin
            out <= 2;
        end if (B == C) begin
            out <= 3;
        end else begin
            out <= 0;
        end
    end

endmodule