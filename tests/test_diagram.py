import shutil
import subprocess
from pathlib import Path

import pytest

from sphinx_svdoc.diagram import connections, interface_dot
from sphinx_svdoc.parser import parse_file

DATA = Path(__file__).parent / "data"


def conns(fname, module):
    mod = {m.name: m for m in parse_file(DATA / fname)}[module]
    return {c.label: c for c in connections(mod)}, mod


def test_bundles_become_single_connections():
    c, _ = conns("groups.sv", "groups")
    apb = c["APB completer"]                 # psel/paddr/pwdata in, prdata out
    assert (apb.direction, apb.side, apb.bus) == ("both", "L", True)
    assert "psel" not in c and "prdata[15:0]" not in c
    # categorised ports outside bundles are drawn individually
    assert {"clk", "rst_n", "host_irq_ack", "led_o[3:0]", "test_mode"} <= set(c)
    assert c["led_o[3:0]"].side == "R"


def test_categories_add_space_between_wires():
    from sphinx_svdoc.diagram import CAT_GAP, PITCH, _offsets
    _, mod = conns("groups.sv", "groups")
    left = [x for x in connections(mod) if x.side == "L"]
    assert [x.label for x in left] == ["clk", "rst_n", "APB completer", "host_irq_ack",
                                      "test_mode", "scan_en"]
    ys, _ = _offsets(left)
    steps = [round(b - a, 1) for a, b in zip(ys, ys[1:])]
    assert steps == [PITCH, PITCH + CAT_GAP, PITCH, PITCH + CAT_GAP, PITCH]


def test_ungrouped_ports_show_width_and_direction(tmp_path):
    f = tmp_path / "u.sv"
    f.write_text("module u (input logic [7:0] data, output logic irq, inout wire pad,\n"
                 "          output logic dbg   // :nodoc:\n);\nendmodule\n")
    (mod,) = parse_file(f)
    c = {x.label: x for x in connections(mod)}
    assert list(c) == ["data[7:0]", "irq", "pad"]            # :nodoc: port left out
    assert (c["data[7:0]"].direction, c["data[7:0]"].bus, c["data[7:0]"].side) == ("in", True, "L")
    assert (c["irq"].direction, c["irq"].bus, c["irq"].side) == ("out", False, "R")
    assert (c["pad"].direction, c["pad"].side) == ("both", "L")   # inout


def test_category_ports_drawn_individually_without_hidden():
    c, _ = conns("nodoc.sv", "nodoc")
    assert list(c) == ["clk", "dbg_b", "data[7:0]"]           # dbg_a, scan_en hidden


def test_mixed_bundle_is_two_way_on_majority_side():
    c, _ = conns("arbiter.sv", "ahb_arb")
    mgr = c["AHB manager <n> (n = 0 … 2)"]                  # 2 in, 1 out
    assert (mgr.direction, mgr.side) == ("both", "L")
    assert c["led<n>_r (n = 0, 1)"].side == "R"
    assert not c["hclk"].bus


def test_dot_has_params_and_two_way_edges():
    _, mod = conns("arbiter.sv", "ahb_arb")
    src = interface_dot(mod)
    assert "layout=neato" in src and "N = 4" in src
    assert src.count("dir=both") == 2                       # manager bundle + m3 bundle


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz not installed")
@pytest.mark.parametrize("fname, module", [("arbiter.sv", "ahb_arb"), ("fifo.sv", "fifo"),
                                           ("groups.sv", "groups")])
def test_dot_renders(fname, module, tmp_path):
    _, mod = conns(fname, module)
    proc = subprocess.run(["dot", "-Tsvg"], input=interface_dot(mod), text=True,
                          capture_output=True)
    assert proc.returncode == 0 and "<svg" in proc.stdout, proc.stderr
    assert "Warning" not in proc.stderr, proc.stderr
