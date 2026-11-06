"""Build svdoc's own documentation (which documents docs/examples) strictly."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

DOCS = Path(__file__).parent.parent / "docs"


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz not installed")
def test_docs_build_without_warnings(tmp_path):
    proc = subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going", "-q",
                           "-b", "html", str(DOCS), str(tmp_path / "html")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    html = (tmp_path / "html" / "structure.html").read_text()
    assert "Manager &lt;n&gt; (n = 0 … 3)" in html          # repeated bundles
    assert "dbg_wait&lt;n&gt;" in html                        # collapsed ports
    assert (tmp_path / "html" / "_images" / "apb_gpio.svg").exists()
