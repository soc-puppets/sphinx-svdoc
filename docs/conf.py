# sphinx-svdoc's own documentation, built with sphinx-svdoc.
#
#   pip install -e ".[sphinx]"
#   sphinx-build -W -b html docs docs/_build/html

from sphinx_svdoc import __version__

project = "sphinx-svdoc"
release = version = __version__

extensions = ["sphinx_svdoc", "sphinx.ext.graphviz"]

# The example modules shown throughout these pages
svdoc_sources = ["examples/*.sv"]
svdoc_source_root = "."            # show paths as examples/<file>.sv

graphviz_output_format = "svg"
pygments_style = "sphinx"
html_theme = "alabaster"
html_theme_options = {"description": "SystemVerilog module docs for Sphinx",
                      "fixed_sidebar": True}
exclude_patterns = ["_build"]
