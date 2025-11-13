///////////////////////////////////////////////////////////////////////////////
//// This module sorts two values (new and current), and keeps the highest one
//// but also detects if the previous block has taken a new value
//// In that case this block will take the previous blocks value instead
////
//// Since this is a single sort module, a chain of these can be used to sort
//// multiple numbers.
//// The first module in the chain will end up with the client/value pair that
//// has the highest value
////
//// In total the sorting process will take n cycles, n being the number of cascaded stages
///////////////////////////////////////////////////////////////////////////////
module single_sort #(
  parameter CLIENTS_BWIDTH_P = 2    // Total bit width of the client ID
)
(
  input   logic                         clk,
  input   logic                         rst,
  input   logic                         enable,
  input   logic                         clr,
  input   logic [7:0]                   new_val,
  input   logic [CLIENTS_BWIDTH_P-1:0]  new_client,
  input   logic [7:0]                   prev_val,
  input   logic [CLIENTS_BWIDTH_P-1:0]  prev_client,
  output  logic [7:0]                   current_val,
  output  logic [CLIENTS_BWIDTH_P-1:0]  current_client
);
//-------------------------------------------------
// Registers for the current value and client
// Determines if the new client entry fits in this location
//-------------------------------------------------
  always_ff @( posedge clk, posedge rst ) begin
    if (rst) begin
      current_val         <= '0;
      current_client      <= '0;
    end else if (clr == 1'b1) begin
      current_val         <= '0;
      current_client      <= '0;
    end else begin
      if (enable == 1'b1) begin
        if ( new_val > current_val ) begin // Enabled?, and does the new client have higher priority than current client ?
          if (new_val > prev_val) begin    // New client has higher priority than the prevoius client
            current_val     <= prev_val;   // Thus we know the new client should be further up the chain
            current_client  <= prev_client;
          end else begin                    // New client don't have higher priority than prevoius client
            current_val     <= new_val;     // Thus we know that the new client should be in this location
            current_client  <= new_client;
          end
        end
      end
    end
  end
endmodule
