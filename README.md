# sphinx-svdoc

sphinx-svdoc documents SystemVerilog modules from their source code, as a Sphinx
extension: think `autodoc`, for RTL. It reads documentation comments next
to parameters and ports, and renders each module's interface as tables and
a block diagram.

* **Black-box.** A module is documented by its interface: header comment,
  parameters and ports. Internals are opt-in.
* **Comments stay readable.** Descriptions are ordinary trailing comments,
  and longer text is reStructuredText.
* **Structure.** Ports can be organised into categories, and signals that
  form one connection (an APB or AHB port) into bundles, which can repeat.
* **Standalone.** Parsing uses [pyslang](https://github.com/MikePopoloski/slang)
  at the syntax level: no elaboration, include paths or complete design.

```systemverilog
/// Synchronous FIFO with registered status flags.
module sync_fifo #(
  parameter int WIDTH = 8               // Data width in bits
) (
  // :category: Clock and reset
  input  logic             clk,         // Clock
  input  logic             rst_n,       // Asynchronous reset, active low
  ...
```

## Quick start

```sh
pip install -e ".[sphinx]"
```

```python
# conf.py
extensions = ["sphinx_svdoc", "sphinx.ext.graphviz"]
svdoc_sources = ["../rtl/*.sv"]
```

```rst
.. sv:automodule:: sync_fifo
```

Diagrams need Graphviz's `dot` on the build machine (`apt install graphviz`).

## Documentation

The full documentation is a Sphinx project in `docs/`, built with sphinx-svdoc
itself. Its examples are real SystemVerilog files in `docs/examples/`.

```sh
pip install -e ".[docs]"
sphinx-build -W -b html docs docs/_build/html
```

## Alternatives

Other tools document SystemVerilog too: [sphinx-systemverilog](https://pypi.org/project/sphinx-systemverilog/),
[svdoc](https://pypi.org/project/svdoc/), [VeriScribe](https://github.com/OYounis/VeriScribe),
[DoxNet](https://github.com/BTFLV/DoxNet), Doxygen with a SystemVerilog filter,
Natural Docs, TerosHDL, [SVDocGraph](https://github.com/lionnus/svdocgraph),
[Symbolator](https://github.com/hdl/symbolator) and
[sphinxcontrib-hdl-diagrams](https://sphinxcontrib-hdl-diagrams.readthedocs.io/).
The "Alternatives" page of the documentation explains why sphinx-svdoc
exists alongside them.

## Development

```sh
pip install -e ".[test]"
pytest
```

The tests include a strict build of the documentation.
