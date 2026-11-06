sphinx-svdoc
============

sphinx-svdoc documents SystemVerilog modules from their source code, as a Sphinx
extension: think ``autodoc``, for RTL. It reads documentation comments
next to parameters and ports, and renders each module's interface as
tables and a block diagram.

* **Black-box.** A module is documented by its interface: header comment,
  parameters and ports. Internals are opt-in.
* **Comments stay readable.** Descriptions are ordinary trailing comments,
  and longer text is reStructuredText, so lists, notes and figures work.
* **Structure.** Ports can be organised into categories, and signals that
  form one connection (an APB or AHB port) into bundles, which can repeat.
* **Standalone.** Parsing uses `pyslang <https://github.com/MikePopoloski/slang>`_
  at the syntax level, so no elaboration, include paths or complete design
  are needed.

Every example on these pages is a real SystemVerilog file in
``docs/examples``, documented by sphinx-svdoc as part of building this site.

.. sv:interface:: apb_gpio

.. toctree::
   :maxdepth: 2

   quickstart
   comments
   structure
   diagrams
   reference
   alternatives
