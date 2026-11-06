Diagrams
========

Interface diagrams
------------------

Each module documented with ``sv:automodule`` gets a block diagram of its
interface: a box with the module name and parameters, and one wire per
connection. To place one on its own, use ``sv:interface``:

.. code-block:: rst

   .. sv:interface:: ahb_arbiter

.. sv:interface:: ahb_arbiter

* A **bundle** is a single connection labelled with its title. Every other
  port gets a wire of its own, labelled with its width.
* **Categories** are not drawn, but their wires are kept together, with
  extra space between one category and the next.
* **Arrows** show direction: into the box (all inputs), out of it (all
  outputs), or both ways (a bundle with a mix, or an ``inout`` port).
* Inputs are on the left and outputs on the right. A two-way connection
  goes on the side of its majority direction.
* **Buses** (bundles and multi-bit ports) are thick. Single bits are thin.
* The box lists the parameters that can be set. Localparams in ``#( … )``
  are derived constants, so they appear in the parameter table but not
  here.
* Hidden ports are left out. Repeated bundles and collapsed ports show
  their index range.

Diagrams need ``sphinx.ext.graphviz`` and Graphviz's ``dot``. They are on
by default; turn them off with ``svdoc_show_diagram = False`` in
``conf.py`` or ``:no-diagram:`` on a module.

Hierarchy
---------

``sv:hierarchy`` draws which modules instantiate which, either for the
whole design or from a given top module. Edges are labelled with instance
names; modules that aren't among the documented sources are dashed.

.. code-block:: rst

   .. sv:hierarchy:: soc_top

.. sv:hierarchy:: soc_top

With ``:style: list``, or without ``sphinx.ext.graphviz``, it is a nested
list instead:

.. sv:hierarchy:: soc_top
   :style: list
