/// Categories and bundles.
module groups #(
  // :category: Sizing
  parameter int AW = 8,              // Address width
  localparam int DW = 16             // Data width (fixed)
) (
  // :category: Clock and reset
  input  logic        clk,
  input  logic        rst_n,

  // :category: Host
  //   Everything facing the host.
  // :bundle: APB completer
  //   Register access from the JTAG TAP. Zero wait states;
  //   ``pslverr`` is never asserted.
  //
  //   * Byte addressed
  //   * 16-bit data
  input  logic        psel,
  input  logic [7:0]  paddr,         // Byte address
  // a plain note, ignored

  /// Write data
  input  logic [15:0] pwdata,
  output logic [15:0] prdata,
  // :endbundle:
  input  logic        host_irq_ack,  // Back in "Host", outside the bundle

  /* :category: LEDs
     Active high. See the board schematic.

     .. figure:: img/blk.svg
  */
  output logic [3:0]  led_o,
  // :endcategory:

  input  logic        test_mode,     // Uncategorised after the marker
  input  logic        scan_en
);
  // :category: Opcodes
  localparam OP_A = 2'd0;
  logic unused;
  localparam OP_B = 2'd1;            // still "Opcodes": only markers change category
  parameter  P_BODY = 3;             // body parameter with a #() list -> localparam
endmodule
