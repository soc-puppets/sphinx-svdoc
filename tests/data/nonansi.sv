// Old-style port list.
module old_style (a, b, y);
  parameter W = 1;    // Body parameter, no #() list: overridable
  localparam L = 2;   // Internal
  input a, b;
  output y;
  assign y = a & b;
endmodule

/// Bus interface.
interface simple_bus #(parameter int AW = 8) (input logic clk);
  logic [AW-1:0] addr;
endinterface
