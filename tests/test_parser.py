from pathlib import Path

import pytest

from sphinx_svdoc.parser import collect_files, parse_file

DATA = Path(__file__).parent / "data"


@pytest.fixture(scope="module")
def fifo():
    (mod,) = parse_file(DATA / "fifo.sv")
    return mod


def by_name(items):
    return {i.name: i for i in items}


def test_header_summary_and_body(fifo):
    assert fifo.summary == "Simple synchronous FIFO."
    assert "Copyright" not in fifo.body            # banner separated by blank line
    assert ".. note:: Not first-word-fall-through." in fifo.body
    assert ":author: A. Engineer" in fifo.body     # non-override fields stay in body
    assert ":param" not in fifo.body and ":port" not in fifo.body


def test_field_overrides(fifo):
    p = by_name(fifo.params)
    assert p["WIDTH"].doc == "Data width in bits. Continued on an indented line."
    assert by_name(fifo.ports)["rd_en"].doc == "Read strobe"


def test_inline_docs(fifo):
    p = by_name(fifo.params)
    assert p["DEPTH"].doc == "Number of entries (power of 2)"   # ///<
    assert p["T"].type == "type" and p["T"].default == "logic [WIDTH-1:0]"
    ports = by_name(fifo.ports)
    assert ports["clk"].doc == "Clock"                         # trailing //
    assert ports["wr_en"].doc == "Write enable; ignored when full"   # /// above


def test_categories(fifo):
    ports = by_name(fifo.ports)
    assert ports["clk"].category == ports["rst_n"].category == "Clock and reset"
    assert ports["wr_en"].category == ports["wdata"].category == "Write side"
    assert ports["rdata"].category == "Read side"
    assert not any(p.bundle for p in fifo.ports)


def test_inherited_port_direction(fifo):
    ports = by_name(fifo.ports)
    assert (ports["empty"].kind, ports["empty"].type) == ("output", "logic")


def test_locals_and_instances(fifo):
    aw = by_name(fifo.locals)["AW"]
    assert aw.default == "$clog2(DEPTH)" and aw.doc == "address_width_"
    assert aw.category == ""       # plain banner comments are not markers
    assert [(i.module, i.name) for i in fifo.instances] == [("fifo_ram", "u_ram")]


def test_nonansi_and_interface():
    old, bus = parse_file(DATA / "nonansi.sv")
    assert old.summary == "Old-style port list."
    assert [p.name for p in old.ports] == ["a", "b", "y"]
    assert bus.keyword == "interface" and bus.summary == "Bus interface."
    assert by_name(bus.params)["AW"].default == "8"


def test_collect_files_glob_and_dir():
    assert {p.name for p in collect_files([DATA])} == {"arbiter.sv", "fifo.sv", "groups.sv", "nodoc.sv", "nonansi.sv", "withimg.sv"}
    assert [p.name for p in collect_files([str(DATA / "fi*.sv")])] == ["fifo.sv"]


def test_categories_and_bundles():
    (mod,) = parse_file(DATA / "groups.sv")
    p = by_name(mod.ports)
    where = lambda n: (p[n].category, p[n].bundle)
    assert where("clk") == where("rst_n") == ("Clock and reset", "")
    for n in ("psel", "paddr", "pwdata", "prdata"):          # blank line + note inside
        assert where(n) == ("Host", "APB completer")
    assert where("host_irq_ack") == ("Host", "")              # :endbundle:
    assert where("led_o") == ("LEDs", "")
    assert where("test_mode") == where("scan_en") == ("", "")  # :endcategory:
    assert p["paddr"].doc == "Byte address" and p["pwdata"].doc == "Write data"
    assert mod.category_docs["Host"] == "Everything facing the host."
    assert ".. figure:: img/blk.svg" in mod.category_docs["LEDs"]
    desc = mod.bundle_docs["APB completer"]
    assert desc.startswith("Register access from the JTAG TAP.")
    assert "* Byte addressed\n* 16-bit data" in desc        # RST structure kept
    assert "Clock and reset" not in mod.category_docs       # title only
    lp = by_name(mod.locals)
    assert lp["OP_A"].category == lp["OP_B"].category == "Opcodes"  # code in between


def test_parameter_classification():
    (mod,) = parse_file(DATA / "groups.sv")
    params = by_name(mod.params)
    assert (params["AW"].kind, params["DW"].kind) == ("parameter", "localparam")
    assert params["DW"].doc == "Data width (fixed)"            # header localparam documented
    assert by_name(mod.locals)["P_BODY"].kind == "localparam"  # body param with #() list
    old, _ = parse_file(DATA / "nonansi.sv")
    assert [(i.name, i.kind) for i in old.params] == [("W", "parameter")]   # no #() list
    assert [(i.name, i.kind) for i in old.locals] == [("L", "localparam")]


def test_nodoc():
    (mod,) = parse_file(DATA / "nodoc.sv")
    hidden = {i.name for i in mod.params + mod.ports + mod.locals if i.hidden}
    assert hidden == {"SIM_SPEEDUP", "dbg_a", "scan_en", "MAGIC"}
    assert [p.name for p in mod.doc_params] == ["WIDTH"]
    assert [p.name for p in mod.doc_ports] == ["clk", "dbg_b", "data"]
    ports = by_name(mod.ports)
    assert (ports["dbg_b"].kind, ports["dbg_b"].type) == ("output", "logic")
    assert ports["dbg_b"].category == ports["data"].category == "Bus"  # category unaffected
    assert [i.name for i in mod.localparams] == ["AW"]


def test_repeated_bundles():
    (mod,) = parse_file(DATA / "arbiter.sv")
    ports = mod.ports
    names = [p.name for p in ports]
    assert names[:6] == ["hclk", "m<n>_hsel", "m<n>_haddr", "m<n>_hready",
                         "s<n>_hsel", "s<n>_haddr"]
    assert mod.bundle_repeat == {"AHB manager <n>": ["0", "1", "2"],
                                 "Subordinate port <n>": ["a", "b"]}
    assert all(p.category == "Bus ports" for p in ports[1:9])
    assert by_name(ports)["m<n>_hready"].doc == "Transfer done for manager <n>"
    assert mod.bundle_docs["AHB manager <n>"].startswith("Requests from bus manager n.")
    assert ":repeat:" not in "".join(mod.bundle_docs.values())
    # different width -> not a copy, documented as written
    assert ["m3_hsel", "m3_haddr", "m3_hready"] == names[6:9]


def test_repeated_rows():
    (mod,) = parse_file(DATA / "arbiter.sv")
    rows = {p.name: p for p in mod.ports if not p.bundle and not p.category}
    assert rows["led<n>_r"].indices == ["0", "1"] and rows["led<n>_r"].doc == "Red"
    assert rows["irq<n>"].doc == "Interrupt <n>" and rows["irq<n>"].indices == ["3", "4"]
    assert "test1" in rows and "led_r" in rows          # singletons / no index


def test_fmt_range():
    from sphinx_svdoc.repeat import fmt_range
    assert fmt_range(["0", "1", "2", "3"]) == "0 … 3"
    assert fmt_range(["0", "1"]) == "0, 1"
    assert fmt_range(["0", "2", "5"]) == "0, 2, 5"
    assert fmt_range(["a", "b", "c", "d"]) == "a … d"


def test_diff_index():
    from sphinx_svdoc.repeat import diff_index
    assert diff_index("m0_x", "m10_x") == (1, "0", "10")
    assert diff_index("sa_x", "sb_x") == (1, "a", "b")
    assert diff_index("kayak", "kbyak") is None         # letter inside a word
    assert diff_index("porta", "portb") == (4, "a", "b")  # trailing letter is fine
    assert diff_index("led_r", "led_g", letters=True) == (4, "r", "g")
    assert diff_index("abc", "abc") is None


MARKER_RULES = """\
module g (
  // A plain section comment: not a marker, not a description
  input  logic a,             // A trailing comment is a description
  // ----------------------------------------
  // :category: Bus
  //   Category description.
  // ----------------------------------------

  /// Doc for b
  input  logic b,
  // plain note about c, ignored
  input  logic c,
  /// :bundle: Doc-style bundle
  ///   Its description, written with ///.
  input  logic d,
  /* :bundle: Block bundle
     Block description. */
  output logic e,
  /* A block comment that mentions :bundle: later is not a marker */
  output logic f,
  // :category: Next
  input  logic g,             // a new category also ends the open bundle
  // :group: Old
  input  logic h              // retired markers are plain comments
);
  // Opcodes, a plain comment: not a category
  localparam OP_A = 0;
  // :category: Widths
  localparam W = 8;
endmodule
"""


def test_marker_rules(tmp_path):
    f = tmp_path / "g.sv"
    f.write_text(MARKER_RULES)
    (mod,) = parse_file(f)
    p = by_name(mod.ports)
    where = lambda n: (p[n].category, p[n].bundle)
    assert where("a") == ("", "") and p["a"].doc == "A trailing comment is a description"
    assert where("b") == ("Bus", "") and p["b"].doc == "Doc for b"   # marker may be gapped
    assert where("c") == ("Bus", "") and p["c"].doc == ""            # plain comment ignored
    assert where("d") == ("Bus", "Doc-style bundle") and p["d"].doc == ""
    assert mod.bundle_docs["Doc-style bundle"] == "Its description, written with ///."
    assert mod.category_docs["Bus"] == "Category description."       # banners dropped
    assert where("e") == where("f") == ("Bus", "Block bundle")       # f: not a new marker
    assert mod.bundle_docs["Block bundle"] == "Block description."
    assert where("g") == ("Next", "")
    assert where("h") == ("Next", "")
    lp = by_name(mod.locals)
    assert (lp["OP_A"].category, lp["OP_A"].doc) == ("", "")
    assert lp["W"].category == "Widths"
