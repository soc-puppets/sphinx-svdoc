Writing documentation comments
==============================

The examples on this page use the ``sync_fifo`` module from
:doc:`quickstart`.

The module description
----------------------

The comment block directly before ``module`` describes it. Any comment
style works: ``//``, ``///``, ``/* */`` or ``/** */``. A comment separated
from ``module`` by a blank line, such as a copyright banner, is ignored.

.. literalinclude:: examples/sync_fifo.sv
   :language: systemverilog
   :end-at: module sync_fifo

* The first paragraph is the **summary**.
* Everything after it is **reStructuredText**, passed straight to Sphinx,
  so notes, lists, links and figures all work.
* ``:param NAME:`` and ``:port NAME:`` fields describe a parameter or port,
  overriding any inline comment. Other fields, such as ``:author:``, are
  shown as written.

Parameters and ports
--------------------

A parameter or port is described by, in order of preference:

#. a ``///`` comment on the line(s) directly above it;
#. a comment at the end of its line (``//``, ``///<`` or ``//!<``);
#. a ``:param:`` or ``:port:`` field in the module description, which
   overrides both.

Plain ``//`` comments on their own line are ordinary code comments and
are ignored, so section headings and notes for source readers never leak
into the documentation.

.. literalinclude:: examples/sync_fifo.sv
   :language: systemverilog
   :start-after: module sync_fifo
   :end-at: );

In ``output logic full, empty``, ``empty`` takes its direction and type
from ``full``, as SystemVerilog does.

Types and widths are shown exactly as written, such as
``logic [WIDTH-1:0]``, so the documentation shows which parameters a port
depends on.

Port and parameter comments are plain text: characters that mean
something in reStructuredText are escaped. Use ````double backticks```` to
mark code.

Hiding items
------------

Mark a parameter, port, localparam or typedef with ``:nodoc:``, as its
trailing comment or on the line directly above it. Any text after the
marker is a note for source readers and is not shown. In ``sync_fifo``,
``SIM_CHECKS`` is hidden this way.

Hidden items are still parsed, so categories, bundles and direction
inheritance work as usual.

Parameters and internals
------------------------

Everything in the ``#( … )`` list is part of the interface and is
documented, including localparams there, which are marked as such
(``AW`` above). In a module without a ``#( … )`` list, ``parameter``
declarations in the body are its real parameters, and are documented too.

Localparams and typedefs in the module body, and the submodules a module
instantiates, are internals. They are shown only on request, with the
``:locals:`` and ``:instances:`` options (or the matching ``conf.py``
settings; see :doc:`reference`). The same module with ``:locals:``:

.. code-block:: rst

   .. sv:automodule:: sync_fifo
      :locals:
      :no-diagram:
      :no-index:

.. sv:automodule:: sync_fifo
   :locals:
   :no-diagram:
   :no-index:

``:no-index:`` is only needed here because ``sync_fifo`` is documented
twice on this site.

Images and included files
-------------------------

Paths in the module description are written **relative to the .sv
file**. sphinx-svdoc rewrites them for whichever page ends up containing the
module. ``apb_gpio`` uses a figure from ``examples/img``:

.. literalinclude:: examples/apb_gpio.sv
   :language: systemverilog
   :end-before: module apb_gpio

This applies to ``image``, ``figure``, ``include``, ``literalinclude``,
``graphviz``, the ``:file:`` option of ``csv-table`` and ``raw``, and the
third-party ``wavedrom``, ``plantuml``, ``kroki``, ``drawio-image`` and
``drawio-figure`` directives. Paths starting with ``/`` (Sphinx's
"relative to the source directory") and URLs are left alone. The files may
live outside the Sphinx source tree. The rendered module is on
:doc:`structure`.
