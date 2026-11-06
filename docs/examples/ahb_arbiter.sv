/// Fixed-priority AHB arbiter for four managers and two subordinates.
module ahb_arbiter #(
  parameter int AW = 32                // Address width
) (
  // :category: Clock and reset
  input  logic          hclk,          // Bus clock
  input  logic          hresetn,       // Bus reset, active low

  // :category: Managers
  // :bundle: Manager 0
  //   :repeat:
  //   Requests from bus manager n. A lower n wins arbitration.
  input  logic          m0_hbusreq,    // Bus request from manager 0
  input  logic [AW-1:0] m0_haddr,      // Address
  output logic          m0_hgrant,     // Bus granted to manager 0
  // :bundle: Manager 1
  input  logic          m1_hbusreq,
  input  logic [AW-1:0] m1_haddr,
  output logic          m1_hgrant,
  // :bundle: Manager 2
  input  logic          m2_hbusreq,
  input  logic [AW-1:0] m2_haddr,
  output logic          m2_hgrant,
  // :bundle: Manager 3
  input  logic          m3_hbusreq,
  input  logic [AW-1:0] m3_haddr,
  output logic          m3_hgrant,

  // :category: Subordinates
  // :bundle: Subordinate A
  //   :repeat:
  //   Select and address for one decoded region.
  output logic          sa_hsel,
  output logic [AW-1:0] sa_haddr,
  // :bundle: Subordinate B
  output logic          sb_hsel,
  output logic [AW-1:0] sb_haddr,

  // :category: Debug
  output logic          dbg_wait0,     // Manager 0 is waiting for a grant
  output logic          dbg_wait1,     // Manager 1 is waiting for a grant
  output logic          dbg_wait2,     // Manager 2 is waiting for a grant
  output logic          dbg_wait3      // Manager 3 is waiting for a grant
);
endmodule
