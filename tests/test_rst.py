import subprocess
import sys
from pathlib import Path

import docutils.core

from sphinx_svdoc.rst import lit, text

DATA = Path(__file__).parent / "data"


def test_text_escaping():
    assert text("address_width_") == r"address\_width\_"
    assert text("use ``foo_bar`` here") == "use ``foo_bar`` here"
    assert text("- not a list") == r"\- not a list"
    assert text("*x*") == r"\*x\*"


def test_lit():
    assert lit("logic [7:0]") == "``logic [7:0]``"
    assert lit("`WIDTH") == r":code:`\`WIDTH`"


def test_cli_rst_is_valid_docutils(tmp_path):
    subprocess.run([sys.executable, "-m", "sphinx_svdoc.cli", "-o", str(tmp_path), str(DATA)],
                   check=True)
    pages = sorted(p.name for p in tmp_path.glob("*.rst"))
    assert pages == ["ahb_arb.rst", "fifo.rst", "groups.rst", "index.rst", "nodoc.rst", "old_style.rst", "simple_bus.rst", "withimg.rst"]
    # Module pages must be clean docutils (index uses Sphinx-only :doc:/toctree)
    for page in ("ahb_arb.rst", "fifo.rst", "groups.rst", "old_style.rst", "simple_bus.rst", "withimg.rst"):
        docutils.core.publish_doctree(
            (tmp_path / page).read_text(),
            settings_overrides={"halt_level": 2, "report_level": 2})


def test_cli_md(tmp_path):
    subprocess.run([sys.executable, "-m", "sphinx_svdoc.cli", "-f", "md", "-o", str(tmp_path),
                    str(DATA / "fifo.sv")], check=True)
    md = (tmp_path / "fifo.md").read_text()
    assert "| `DEPTH` | `int` | `16` | Number of entries (power of 2) |" in md


def test_rebase_paths():
    from sphinx_svdoc.rst import rebase_paths
    body = ("..  figure:: img/a.svg\n   :width: 50%\n\n"
            ".. image:: https://x.org/b.png\n.. image:: /abs/c.png\n"
            ".. csv-table:: T\n   :file: tables/t.csv\n.. include:: <isonum.txt>")
    out = rebase_paths(body, "/w/rtl/blk", "/w/doc/api").splitlines()
    assert out[0] == "..  figure:: ../../rtl/blk/img/a.svg"
    assert out[1] == "   :width: 50%"
    assert out[3] == ".. image:: https://x.org/b.png"
    assert out[4] == ".. image:: /abs/c.png"
    assert out[6] == "   :file: ../../rtl/blk/tables/t.csv"
    assert out[7] == ".. include:: <isonum.txt>"


def test_nodoc_not_rendered():
    from sphinx_svdoc.parser import parse_file
    from sphinx_svdoc.rst import render_module
    (mod,) = parse_file(DATA / "nodoc.sv")
    out = "\n".join(render_module(mod, include_locals=True))
    for name in ("SIM_SPEEDUP", "dbg_a", "scan_en", "MAGIC", "nodoc:"):
        assert name not in out.replace("sv:module:: nodoc", "")
    assert "``dbg_b``" in out and "``AW``" in out
