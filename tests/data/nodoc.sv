/// Hiding items from the documentation.
module nodoc #(
  parameter int WIDTH = 8,          // Data width
  parameter int SIM_SPEEDUP = 0     // :nodoc: simulation only
) (
  // :category: Bus
  input  logic        clk,          // Clock
  // :nodoc:
  output logic        dbg_a,        // trailing text is ignored when hidden
                      dbg_b,        // Inherits output logic from hidden dbg_a
  /// :NoDoc:
  input  logic        scan_en,
  input  logic [7:0]  data          // Data
);
  localparam int AW = 4;            // Address width
  localparam int MAGIC = 42;        // :nodoc:
endmodule
