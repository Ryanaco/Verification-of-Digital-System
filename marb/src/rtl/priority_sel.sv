///////////////////////////////////////////////////////////////////////////////
//// Module selects the client priorty based on the ctrl.mode and the clients priorities
//// Also instanciates and controls a cascade of 'single sorter' modules
///////////////////////////////////////////////////////////////////////////////
module priority_sel #(
  parameter MEM_ARB_CLIENTS_P = 3                      // Number of client interfaces of the arbiter
)
(
  input   logic                                   clk,
  input   logic                                   rst,
  input   ctrl_reg_t                              ctrl,
  input   dprio_reg_t                             dprio         [((((MEM_ARB_CLIENTS_P-1)/4)+1)*4)], // 32bit alligned
  input   logic                                   dprio_wstrb,
  // Icarus workaround, separate signals for each priority list
  output  logic [$clog2(MEM_ARB_CLIENTS_P)-1:0]   prio_list0,
  output  logic [$clog2(MEM_ARB_CLIENTS_P)-1:0]   prio_list1,
  output  logic [$clog2(MEM_ARB_CLIENTS_P)-1:0]   prio_list2
);

  localparam CLIENTS_BWIDTH_P   = $clog2(MEM_ARB_CLIENTS_P);  // Bit width to represent all clients

  logic [7:0]                   temp_val            [MEM_ARB_CLIENTS_P];
  logic [7:0]                   new_val;
  logic [CLIENTS_BWIDTH_P-1:0]  new_client;

  logic [CLIENTS_BWIDTH_P-1:0]  count, next_count;

  sorter_states_t               sort_state;
  logic                         sorter_en, sorter_clr;

  logic [CLIENTS_BWIDTH_P-1:0]  client_list_static  [MEM_ARB_CLIENTS_P];
  logic [CLIENTS_BWIDTH_P-1:0]  client_list_dyn     [MEM_ARB_CLIENTS_P];

  logic [$clog2(MEM_ARB_CLIENTS_P)-1:0]   priority_list [MEM_ARB_CLIENTS_P];

  // Assign priority lists to priority list array
  assign prio_list0 = priority_list[0];
  assign prio_list1 = priority_list[1];
  assign prio_list2 = priority_list[2];

//-------------------------------------------------
// Generate a static priority list
// The priority will end up as [0] = client0, [1] = client1 etc.
// Meaning that client0 has the highest priority when using static priority
//-------------------------------------------------
  genvar j;
  generate
    for (j = 0; j < MEM_ARB_CLIENTS_P; j++) begin: generate_static_priority_list
      assign client_list_static[j]  = j;
    end
  endgenerate

///////////////////////////////////////////////////////////////////////////////
//// Priority switch logic
///////////////////////////////////////////////////////////////////////////////
//-------------------------------------------------
// Switches between static and dynamic priority according to the operating mode
// In dynamic mode, priority_list will only be updated when sorting is idle.
// priority_list[0] holds the client with the highest priority
//-------------------------------------------------
  always_ff @( posedge clk, posedge rst ) begin
    if (rst) begin
      // Icarus workaround, cannot assign whole array
      priority_list[0]       <= client_list_static[0];
      priority_list[1]       <= client_list_static[1];
      priority_list[2]       <= client_list_static[2];
    end else begin
      if (ctrl.mode == 1) begin         // Dynamic priority
        if (sort_state == SORTER_IDLE) begin   // We only want to change priority_list when sorting has finished
          priority_list[0]   <= client_list_dyn[0];
          priority_list[1]   <= client_list_dyn[1];
          priority_list[2]   <= client_list_dyn[2];
        end else begin                  // Sorting still ongoing, keep current priority list
          priority_list[0]   <= priority_list[0];
          priority_list[1]   <= priority_list[1];
          priority_list[2]   <= priority_list[2];
        end
      end else begin                    // ctrl.mode != 1 -> fixed priority
        priority_list[0]       <= client_list_static[0];
        priority_list[1]       <= client_list_static[1];
        priority_list[2]       <= client_list_static[2];
      end
    end
  end
  genvar i;

///////////////////////////////////////////////////////////////////////////////
//// Sorter logic
///////////////////////////////////////////////////////////////////////////////
//-------------------------------------------------
// Sorting state machine
//-------------------------------------------------
  always_ff @( posedge clk, posedge rst ) begin
    if (rst) begin
      sort_state              <= SORTER_IDLE;
    end else begin
      case (sort_state)
        SORTER_IDLE: begin
          if (dprio_wstrb != 0) begin                       // Restart counting if dprio has changed since start.
            sort_state        <= SORTER_CLEAR;
          end
        end
        SORTER_CLEAR: sort_state     <= SORTER_SORT;                      // After clear, start sorting
        SORTER_SORT: begin
          if (dprio_wstrb != 0) begin                       // Restart counting if dprio has changed since start of sorting and before finishing
            sort_state        <= SORTER_CLEAR;
          end else if (count == MEM_ARB_CLIENTS_P-1) begin  // Go to IDLE when we have finsihed sorting
            sort_state        <= SORTER_IDLE;
          end
        end
        default: sort_state   <= SORTER_IDLE;
      endcase
    end
  end
//-------------------------------------------------
// Sorting state machine decoding
//-------------------------------------------------
  always_comb begin
    sorter_en       = 1'b0;
    sorter_clr      = 1'b0;
    next_count      = 0;
    case (sort_state)
      SORTER_IDLE: begin     // In IDLE, the sorters should hold its value
        sorter_en   = 1'b0;
        sorter_clr  = 1'b0;
        next_count  = 0;
      end
      SORTER_CLEAR: begin    // Clear the sorters from previous content
        sorter_en   = 1'b0;
        sorter_clr  = 1'b1;
        next_count  = 0;
      end
      SORTER_SORT: begin     // Enable sorting, and start counting
        sorter_en   = 1'b1;
        sorter_clr  = 1'b0;
        next_count  = count + 1;
      end
      default: ;
    endcase
  end
//-------------------------------------------------
// Counter used for iterating through all clients
//-------------------------------------------------
  always_ff @( posedge clk, posedge rst ) begin
    if (rst) begin
      count   <= '0;
    end else begin
      count   <= next_count;
    end
  end

///////////////////////////////////////////////////////////////////////////////
//// Client/dprio entry selection
///////////////////////////////////////////////////////////////////////////////
//-------------------------------------------------
// Selection of the next input value for sorting
//-------------------------------------------------
  assign new_client   = count;
  assign new_val      = dprio[count];

///////////////////////////////////////////////////////////////////////////////
//// Module Instantiations
///////////////////////////////////////////////////////////////////////////////
//-------------------------------------------------
// First 'single sorter' is different than the rest because there is no prev module,
// so we simply take the new input and put it into both prev and new inputs
//-------------------------------------------------
  single_sort #(
    .CLIENTS_BWIDTH_P(CLIENTS_BWIDTH_P)
  ) single_sort_i (
    .clk(clk),
    .rst(rst),
    .enable(sorter_en),
    .clr(sorter_clr),
    .new_val(new_val),
    .new_client(new_client),
    .prev_val(new_val),
    .prev_client(new_client),
    .current_val(temp_val[0]),
    .current_client(client_list_dyn[0])
  );
//-------------------------------------------------
// Generate the rest of the sorters
//-------------------------------------------------
  generate
    for (i = 1; i < MEM_ARB_CLIENTS_P; i++) begin: Single_sorters
      single_sort #(
        .CLIENTS_BWIDTH_P(CLIENTS_BWIDTH_P)
      ) single_sort_i (
        .clk(clk),
        .rst(rst),
        .enable(sorter_en),
        .clr(sorter_clr),
        .new_val(new_val),
        .new_client(new_client),
        .prev_val(temp_val[ i-1 ]),
        .prev_client(client_list_dyn[ i-1 ]),
        .current_val(temp_val[ i ]),
        .current_client(client_list_dyn[ i ])
      );
    end
  endgenerate
endmodule
