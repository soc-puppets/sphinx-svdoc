Alternatives
============

Several other tools document SystemVerilog or Verilog. This page explains
why sphinx-svdoc exists alongside them. It was surveyed in November 2026.
These projects change, so check their current state before you decide.

The requirements that ruled most of them out were:

* **Sphinx integration**, so module documentation lives with the rest of
  a project's documentation and can be cross-referenced.
* **A black-box view** of each module: its interface, documented from
  ordinary comments, with internals left out.
* **Comment conventions** that read naturally in the source: trailing
  comments and reStructuredText, not Doxygen ``@`` tags.
* **Structure**: categories of ports, and bundles of signals that form one
  connection, including repeated bundles.

sphinx-systemverilog
--------------------

`sphinx-systemverilog <https://pypi.org/project/sphinx-systemverilog/>`_ is
a Sphinx autodoc extension built on pyslang, like sphinx-svdoc. It covers
far more of the language, including classes, packages and UVM, and it
elaborates the design, so it can show parameter values per instance and
report errors in the source. Its native comment style is close to
sphinx-svdoc's.

It was the closest match, and we evaluated version 0.6.2 on real RTL. For
module interfaces it fell short:

* The trailing comment on the last port or parameter was lost.
* A section comment above a group of ports became the first port's
  description, replacing that port's own comment.
* ``///<`` comments kept the ``<``, and in ``output logic a, b`` the second
  port lost its direction and type.
* There is no way to categorise ports, bundle them, collapse repeated
  ports, or hide one from the source.
* Image paths in comments are not rewritten relative to the source file.
* Ports are listed one entry each rather than in tables.

The two extensions use the same ``sv`` domain name, so they cannot be
loaded in the same Sphinx project.

svdoc
-----

`svdoc <https://pypi.org/project/svdoc/>`_ is a pydoc-style documentation
generator for SystemVerilog RTL, also built on pyslang, using Doxygen-style
comments. It produces Markdown or HTML pages rather than Sphinx content.
Its name is why this project is called sphinx-svdoc.

VeriScribe
----------

`VeriScribe <https://github.com/OYounis/VeriScribe>`_ parses
SystemVerilog with pyslang and generates HTML, PDF or Markdown, with
WaveDrom and Mermaid diagrams. It uses Doxygen-style ``@`` tags, does not
integrate with Sphinx, and is licensed under the AGPL-3.0.

DoxNet
------

`DoxNet <https://github.com/BTFLV/DoxNet>`_ generates HTML, Markdown,
JSON or PDF documentation from Verilog and SystemVerilog, combining
declarations with Doxygen-style comments. It is a standalone generator,
not a Sphinx extension.

Doxygen with a SystemVerilog filter
-----------------------------------

Doxygen does not understand SystemVerilog, but a filter can rewrite the
source as C++ that it does understand, and
`Breathe <https://breathe.readthedocs.io/>`_ can bring Doxygen's output
into Sphinx (described in
`Documenting SystemVerilog with Sphinx
<https://bitsbytesgates.com/2022/01/24/documenting-systemverilog-with-sphinx.html>`_).
That chains three tools, approximates SystemVerilog as C++ with regular
expressions, and uses Doxygen's ``@`` tags.

Natural Docs
------------

`Natural Docs <https://www.naturaldocs.org/>`_ is a general-purpose
documentation generator with its own comment format, and has been used for
SystemVerilog (see this
`comparison with Doxygen <https://github.com/brabect1/hdl_api_doc_test>`_).
It produces its own site, not Sphinx content, and does not know about
ports and parameters.

TerosHDL
--------

The `TerosHDL <https://terostechnology.github.io/terosHDLdoc/>`_ IDE
includes a documenter that reads ``//!`` comments and generates HTML or
Markdown, with dependency graphs and state-machine diagrams. It is part of
the TerosHDL tooling rather than a Sphinx extension.

SVDocGraph
----------

`SVDocGraph <https://github.com/lionnus/svdocgraph>`_ builds a static
website from a `Bender <https://github.com/pulp-platform/bender>`_ project,
with a clickable hierarchy and per-module port and parameter tables. It
needs a Bender project and does not integrate with Sphinx.

Symbolator
----------

`Symbolator <https://github.com/hdl/symbolator>`_ draws component symbols
for VHDL and Verilog modules and includes a Sphinx extension. It produces
diagrams only, not the surrounding documentation, uses its own HDL parser,
and needs the Cairo and Pango graphics libraries.

sphinxcontrib-hdl-diagrams
--------------------------

`sphinxcontrib-hdl-diagrams <https://sphinxcontrib-hdl-diagrams.readthedocs.io/>`_
is a Sphinx extension that draws diagrams from Verilog using Yosys. The
diagrams show a module's implementation (its netlist) rather than its
interface, and it needs Yosys.
