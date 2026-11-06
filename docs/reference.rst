Reference
=========

Directives
----------

All directives belong to the ``sv`` domain.

``.. sv:automodule:: NAME``
   Document one module from its source.

``.. sv:autoall:: [PATTERN]``
   Document every module, sorted by name, or those matching an
   ``fnmatch`` pattern such as ``ahb_*``. ``:exclude: PATTERN ...`` leaves
   modules out.

``.. sv:interface:: NAME``
   Just the interface diagram of a module.

``.. sv:hierarchy:: [TOP]``
   The instance hierarchy, of the whole design or below ``TOP``.
   ``:style: graphviz`` or ``:style: list`` overrides ``svdoc_hierarchy``.

``.. sv:module:: NAME``
   Describe a module by hand. The content is ordinary reStructuredText.

``sv:automodule`` and ``sv:autoall`` take these options:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - Option
     - Effect
   * - ``:locals:`` / ``:no-locals:``
     - Show or hide body localparams and typedefs
   * - ``:instances:`` / ``:no-instances:``
     - Show or hide the table of submodule instances
   * - ``:diagram:`` / ``:no-diagram:``
     - Show or hide the interface diagram
   * - ``:no-index:``
     - Document the module again without making it a link target or
       index entry

Cross-references
----------------

``:sv:mod:`NAME``` links to a documented module, as in
:sv:mod:`ahb_arbiter`. Modules also appear in the general index and in the
page's table of contents.

Configuration
-------------

.. list-table::
   :header-rows: 1
   :widths: auto

   * - Setting
     - Default
     - Meaning
   * - ``svdoc_sources``
     - ``[]``
     - Globs for the SystemVerilog files to read, relative to ``conf.py``
       (``**`` recurses)
   * - ``svdoc_show_locals``
     - ``False``
     - Show body localparams and typedefs
   * - ``svdoc_show_instances``
     - ``False``
     - Show submodule instance tables
   * - ``svdoc_show_diagram``
     - ``True``
     - Show interface diagrams (needs ``sphinx.ext.graphviz``)
   * - ``svdoc_hierarchy``
     - ``"graphviz"``
     - Default style of ``sv:hierarchy``: ``"graphviz"`` or ``"list"``
   * - ``svdoc_source_root``
     - parent of ``conf.py``
     - Source paths are shown relative to this directory
   * - ``svdoc_source_url``
     - ``None``
     - Link each module's source, for example
       ``"https://github.com/org/repo/blob/main/{path}#L{line}"``

Editing a SystemVerilog file rebuilds every page that documents it.

.. _cli:

Command line
------------

The ``sphinx-svdoc`` command writes one page per module plus an index, without
Sphinx:

.. code-block:: sh

   sphinx-svdoc -o out/ rtl/*.sv                 # plain reStructuredText
   sphinx-svdoc --locals --instances -o out/ rtl/*.sv
   sphinx-svdoc -f md -o out/ -r rtl/            # Markdown, recursing into directories

The reStructuredText output works with plain docutils as well as Sphinx.
Interface diagrams are only drawn by the Sphinx extension.

Limitations
-----------

* Old-style (non-ANSI) port lists, where directions and types are declared
  in the module body, list port names only.
* Functions, tasks, classes and packages are not documented.
