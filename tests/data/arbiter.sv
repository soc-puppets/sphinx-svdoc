/// AHB arbiter with repeated manager ports.
module ahb_arb #(
  parameter int N = 4
) (
  input  logic        hclk,

  // :category: Bus ports
  // :bundle: AHB manager 0
  //   :repeat:
  //   Requests from bus manager n. Lower n wins arbitration.
  input  logic        m0_hsel,       // Select
  input  logic [31:0] m0_haddr,      // Address

  output logic        m0_hready,     // Transfer done for manager 0

  // :bundle: AHB manager 1
  input  logic        m1_hsel,
  input  logic [31:0] m1_haddr,
  output logic        m1_hready,
  // :bundle: AHB manager 2
  input  logic        m2_hsel,
  input  logic [31:0] m2_haddr,
  output logic        m2_hready,

  // :bundle: Subordinate port A
  //   :repeat:
  output logic        sa_hsel,
  output logic [31:0] sa_haddr,
  // :bundle: Subordinate port B
  output logic        sb_hsel,
  output logic [31:0] sb_haddr,

  // :bundle: Not a copy (different width) -> documented normally
  input  logic        m3_hsel,
  input  logic [15:0] m3_haddr,
  output logic        m3_hready,
  // :endcategory:

  output logic        led0_r,        // Red
  output logic        led0_g,        // Green
  output logic        led1_r,        // Red
  output logic        led1_g,        // Green
  output logic        irq3,          // Interrupt 3
  output logic        irq4,          // Interrupt 4
  output logic        test1,         // One-off
  output logic        led_r          // no index
);
endmodule
