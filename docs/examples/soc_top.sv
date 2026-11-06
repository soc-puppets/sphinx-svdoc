/// Example top level, used to show the instance hierarchy.
module soc_top (
  input  logic clk,                    // System clock
  input  logic rst_n                   // System reset, active low
);
  ahb_arbiter u_arbiter (.hclk(clk), .hresetn(rst_n));
  apb_gpio #(.N(16)) u_gpio (.pclk(clk), .presetn(rst_n));
  sync_fifo #(.WIDTH(32)) u_rx_fifo (.clk(clk), .rst_n(rst_n));
  sync_fifo #(.WIDTH(32)) u_tx_fifo (.clk(clk), .rst_n(rst_n));
endmodule
