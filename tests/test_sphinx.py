import shutil
import subprocess
import sys
from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"


def build(tmp_path, extra_conf="", rst=None):
    src = tmp_path / "src"
    src.mkdir()
    (src / "conf.py").write_text(
        f'extensions = ["sphinx_svdoc"]\n'
        f'svdoc_sources = [{str(DATA / "*.sv")!r}]\n{extra_conf}\n')
    (src / "index.rst").write_text(rst or (
        "Top\n===\n\nSee :sv:mod:`fifo`.\n\n"
        ".. sv:hierarchy::\n\n.. sv:autoall::\n"))
    out = tmp_path / "out"
    proc = subprocess.run([sys.executable, "-m", "sphinx", "-W", "-q", "-b", "html",
                           str(src), str(out)], capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"sphinx build failed:\n{proc.stderr}")
    return (out / "index.html").read_text()


def test_autoall_and_xrefs(tmp_path):
    html = build(tmp_path)
    assert 'id="sv-module-fifo"' in html
    assert 'href="#sv-module-fifo"' in html           # :sv:mod: resolved
    assert "Data width in bits." in html               # :param: override
    assert "Not first-word-fall-through." in html      # .. note:: rendered
    assert "Clock and reset" in html                   # category heading


def test_hierarchy_list_fallback(tmp_path):
    # graphviz extension not loaded -> nested list
    html = build(tmp_path)
    assert "u_ram" in html and "<object" not in html


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz not installed")
def test_hierarchy_graphviz(tmp_path):
    html = build(tmp_path, 'extensions.append("sphinx.ext.graphviz")\n'
                           'graphviz_output_format = "svg"')
    assert "graphviz" in html and ".svg" in html


def test_unknown_module_warns(tmp_path):
    with pytest.raises(Exception, match="unknown module"):
        build(tmp_path, rst="Top\n===\n\n.. sv:automodule:: nope\n")


def test_figure_relative_to_sv_file(tmp_path):
    """Image path in the header is relative to the .sv file, the page is in a
    subdirectory, and the SV tree is outside the Sphinx source dir."""
    src = tmp_path / "src"
    (src / "hw" / "blocks").mkdir(parents=True)
    (src / "conf.py").write_text(
        f'extensions = ["sphinx_svdoc"]\nsvdoc_sources = [{str(DATA / "withimg.sv")!r}]\n')
    (src / "index.rst").write_text("Top\n===\n\n.. toctree::\n\n   hw/blocks/withimg\n")
    (src / "hw" / "blocks" / "withimg.rst").write_text(
        "Withimg\n=======\n\n.. sv:automodule:: withimg\n")
    out = tmp_path / "out"
    proc = subprocess.run([sys.executable, "-m", "sphinx", "-W", "-q", "-b", "html",
                           str(src), str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert (out / "_images" / "blk.svg").exists()
    html = (out / "hw" / "blocks" / "withimg.html").read_text()
    assert "../../_images/blk.svg" in html
    assert "Block diagram (path relative to this .sv file)." in html


def test_category_and_bundle_rendering(tmp_path):
    html = build(tmp_path, rst="Top\n===\n\n.. sv:automodule:: groups\n")
    assert 'class="svdoc-category' in html and "svdoc-category-title" in html
    assert 'class="svdoc-bundle' in html and "svdoc-bundle-title" in html
    assert "Everything facing the host." in html
    assert "Zero wait states;" in html and "<li><p>Byte addressed</p></li>" in html
    assert "(localparam)" in html                          # header localparam DW
    assert "svdoc.css" in html
    out = tmp_path / "out"
    assert (out / "_static" / "svdoc.css").exists()
    assert (out / "_images" / "blk.svg").exists()            # figure path rebased


def test_repeat_rendering(tmp_path):
    html = build(tmp_path, rst="Top\n===\n\n.. sv:automodule:: ahb_arb\n")
    assert "AHB manager &lt;n&gt; (n = 0 … 2)" in html
    assert "Subordinate port &lt;n&gt; (n = a, b)" in html
    assert "m&lt;n&gt;_haddr" in html and "m1_haddr" not in html
    assert "(n = 0, 1)" in html                       # led<n>_r row


def test_black_box_by_default(tmp_path):
    html = build(tmp_path, rst="Top\n===\n\n.. sv:automodule:: fifo\n")
    assert "Number of entries" in html                 # parameters and ports shown
    assert "address_width_" not in html                # localparam hidden
    assert "Instances" not in html and "fifo_ram" not in html


@pytest.mark.parametrize("conf, rst", [
    ("svdoc_show_locals = True\nsvdoc_show_instances = True", ""),
    ("", "   :locals:\n   :instances:\n"),
])
def test_show_internals(tmp_path, conf, rst):
    html = build(tmp_path, conf, "Top\n===\n\n.. sv:automodule:: fifo\n" + rst)
    assert "address_width_" in html                    # escaped, not a reference
    assert "Instances" in html and "fifo_ram" in html


def test_no_option_overrides_conf(tmp_path):
    html = build(tmp_path, "svdoc_show_locals = True",
                 "Top\n===\n\n.. sv:automodule:: fifo\n   :no-locals:\n")
    assert "address_width_" not in html


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz not installed")
def test_interface_diagram(tmp_path):
    gv = 'extensions.append("sphinx.ext.graphviz")\ngraphviz_output_format = "svg"'
    html = build(tmp_path, gv, "Top\n===\n\n.. sv:automodule:: groups\n")
    assert "svdoc-interface" in html                       # on by default
    (tmp_path / "b").mkdir()
    html = build(tmp_path / "b", gv,
                 "Top\n===\n\n.. sv:automodule:: groups\n   :no-diagram:\n\n"
                 ".. sv:interface:: fifo\n")
    assert html.count("svdoc-interface") == 1              # only the standalone one


def test_interface_diagram_needs_graphviz(tmp_path):
    html = build(tmp_path, rst="Top\n===\n\n.. sv:automodule:: groups\n")
    assert "svdoc-interface" not in html                   # skipped, no warning
