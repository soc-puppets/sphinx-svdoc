"""sphinx-svdoc: module documentation from SystemVerilog source, for Sphinx.

Enable it in ``conf.py`` with ``extensions = ["sphinx_svdoc"]``.
"""
__version__ = "0.1.0"

from .model import Instance, Item, Module  # noqa: F401
from .parser import collect_files, parse_file  # noqa: F401


def setup(app):
    """Sphinx entry point (``extensions = ["sphinx_svdoc"]``).

    Imported lazily so that the parser and command-line tool work without
    Sphinx installed.
    """
    from .sphinx import setup as _setup
    return _setup(app)
