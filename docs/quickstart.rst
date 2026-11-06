Quick start
===========

Install
-------

sphinx-svdoc needs Python 3.11 or later. Install it, with Sphinx, from a checkout:

.. code-block:: sh

   pip install -e "path/to/sphinx-svdoc[sphinx]"

Interface and hierarchy diagrams use ``sphinx.ext.graphviz``, which comes
with Sphinx, and need Graphviz's ``dot`` program on the build machine
(for example ``apt install graphviz``). Without it, sphinx-svdoc leaves the
interface diagrams out and draws the hierarchy as a list.

Configure
---------

In your Sphinx project's ``conf.py``:

.. code-block:: python

   extensions = ["sphinx_svdoc", "sphinx.ext.graphviz"]

   # SystemVerilog files to read, as globs relative to conf.py
   svdoc_sources = ["../rtl/*.sv", "../ip/**/*.sv"]

Document a module
-----------------

Then, in any page:

.. code-block:: rst

   .. sv:automodule:: sync_fifo

That renders the module's description, an interface diagram, and its
parameter and port tables:

.. sv:automodule:: sync_fifo

The source for that module is below. :doc:`comments` explains how each
comment is used.

.. literalinclude:: examples/sync_fifo.sv
   :language: systemverilog
   :end-at: );

Without Sphinx
--------------

For a quick look without a Sphinx project, the ``sphinx-svdoc`` command writes
plain reStructuredText or Markdown pages; see :ref:`cli`.
