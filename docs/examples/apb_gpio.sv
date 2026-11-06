/// General-purpose I/O with an APB register interface.
///
/// Each pin can be an input or an output. An interrupt is raised when an
/// enabled input changes.
///
/// .. figure:: img/apb_gpio.svg
///    :width: 420px
///
///    Block diagram. The image path is relative to this ``.sv`` file.
module apb_gpio #(
  parameter int N = 8                  // Number of pins
) (
  // :category: Clock and reset
  input  logic         pclk,           // APB clock
  input  logic         presetn,        // APB reset, active low

  // :category: Host
  //   Everything facing the processor.
  // :bundle: APB completer
  //   Register access. Zero wait states; ``pslverr`` is never asserted.
  input  logic         psel,
  input  logic         penable,
  input  logic         pwrite,
  input  logic [7:0]   paddr,          // Byte address

  input  logic [31:0]  pwdata,
  output logic [31:0]  prdata,
  output logic         pready,
  output logic         pslverr,
  // :endbundle:
  output logic         irq,            // Level interrupt: an enabled input changed

  // :category: Pins
  //   Connect to the pad ring.
  input  logic [N-1:0] gpio_i,         // Pin input
  output logic [N-1:0] gpio_o,         // Pin output
  output logic [N-1:0] gpio_oe         // Output enable, active high
);
  assign pready  = 1'b1;
  assign pslverr = 1'b0;
endmodule
