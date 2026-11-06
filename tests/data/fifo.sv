// Copyright (c) 2026 Example Ltd. Licence banner, separated by a blank line.

/// Simple synchronous FIFO.
///
/// Stores up to ``DEPTH`` words. *full* and *empty* are registered.
///
/// .. note:: Not first-word-fall-through.
///
/// :author: A. Engineer
/// :param WIDTH: Data width in bits.
///     Continued on an indented line.
/// :port rd_en: Read strobe
module fifo #(
  parameter int WIDTH = 8,
  parameter int DEPTH = 16,          ///< Number of entries (power of 2)
  parameter type T = logic [WIDTH-1:0]
) (
  // :category: Clock and reset
  input  logic         clk,          // Clock
  input  logic         rst_n,        // Async reset, active low

  // :category: Write side
  /// Write enable; ignored when full
  input  logic         wr_en,
  input  T             wdata,

  // :category: Read side
  input  logic         rd_en,
  output T             rdata,
  output logic         full, empty
);
  // ---------------------------------------------------------------------
  // Derived constants
  // ---------------------------------------------------------------------

  localparam int AW = $clog2(DEPTH); // address_width_
  T mem [DEPTH];

  fifo_ram #(.W(WIDTH)) u_ram (.*);
endmodule
