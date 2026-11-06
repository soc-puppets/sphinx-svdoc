// Copyright (c) 2026 Example Co. This banner is separated from the module
// comment by a blank line, so svdoc ignores it.

/// Synchronous FIFO with registered status flags.
///
/// Stores up to ``DEPTH`` words of ``WIDTH`` bits. Writes to a full FIFO and
/// reads from an empty one are ignored.
///
/// .. note:: Not first-word-fall-through: read data appears the cycle
///    after ``rd_en``.
///
/// :param DEPTH: Number of entries. Must be a power of two.
module sync_fifo #(
  parameter  int WIDTH      = 8,             // Data width in bits
  parameter  int DEPTH      = 16,
  parameter  bit SIM_CHECKS = 1,             // :nodoc: simulation-only assertions
  localparam int AW         = $clog2(DEPTH)  // Address width
) (
  // :category: Clock and reset
  input  logic             clk,              // Clock
  input  logic             rst_n,            // Asynchronous reset, active low

  // :category: Write side
  /// Write enable. Ignored while ``full`` is high.
  input  logic             wr_en,
  input  logic [WIDTH-1:0] wdata,            // Write data

  // :category: Read side
  input  logic             rd_en,            // Read enable
  output logic [WIDTH-1:0] rdata,            // Read data, valid the cycle after rd_en

  // :category: Status
  output logic             full,             // No room for another write
                           empty             // Nothing to read
);
  // Everything below is internal. It is only documented with :locals:.
  localparam int PTR_W = AW + 1;             // Pointer width, with a wrap bit

  logic [WIDTH-1:0] mem [DEPTH];
  logic [PTR_W-1:0] wptr, rptr;

  assign full  = (wptr[AW-1:0] == rptr[AW-1:0]) && (wptr[AW] != rptr[AW]);
  assign empty = (wptr == rptr);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      wptr <= '0;
      rptr <= '0;
    end else begin
      if (wr_en && !full) begin
        mem[wptr[AW-1:0]] <= wdata;
        wptr <= wptr + 1'b1;
      end
      if (rd_en && !empty) begin
        rdata <= mem[rptr[AW-1:0]];
        rptr <= rptr + 1'b1;
      end
    end
  end
endmodule
