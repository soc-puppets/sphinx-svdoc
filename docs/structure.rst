Categories and bundles
======================

Ports can be organised in two ways, both marked explicitly:

* A **category** is an organising heading, such as "Clock and reset",
  "DFT" or "Debug". It only affects how the documentation is laid out.
* A **bundle** is a set of signals that together form one functional
  connection, such as an AHB manager port or an APB completer. It is drawn
  as a single connection on the interface diagram, and can be repeated.
  Bundles sit inside categories.

Markers
-------

.. literalinclude:: examples/apb_gpio.sv
   :language: systemverilog
   :start-at: module apb_gpio
   :end-at: );

* ``// :category: Title`` and ``// :bundle: Title`` start a category or a
  bundle. Further lines in the same comment are its description, written as
  reStructuredText. Any comment style works.
* A category ends at the next ``:category:`` or at ``// :endcategory:``.
  Ports after ``:endcategory:`` are uncategorised.
* A bundle ends at the next ``:bundle:``, at ``// :endbundle:`` (returning
  to the enclosing category, as ``irq`` does above), or when a new category
  starts.
* Blank lines and plain comments never start or end anything.

Parameter lists and localparams can use categories in the same way.

The result:

.. sv:automodule:: apb_gpio

Repeated bundles
----------------

A module with several identical ports, such as an arbiter with four
manager ports, can document them once. Put a ``:repeat:`` line in the first
bundle's description. The bundles that immediately follow it, in the same
category, are merged into it:

.. literalinclude:: examples/ahb_arbiter.sv
   :language: systemverilog
   :start-at: :category: Managers
   :end-before: :category: Subordinates

A following bundle is merged only if it is an exact copy: the same number
of ports, with the same directions and types, and names (and title) that
differ from the first only by one index. The first bundle that isn't a copy
ends the merge and is documented normally, so a real difference is never
hidden. The index can be a number (``m0``, ``m12``) or a single letter
(``sa_hsel``, title "Subordinate A"). Only the first bundle's descriptions
are used, and an index in them ("manager 0") becomes ``<n>``.

Repeated ports outside bundles are collapsed automatically, whether or not
they are in a category. Ports whose names differ only by a number, with the
same direction, type and description (the number may appear in the
description), become one row. Only numbers count, so ``led_r``, ``led_g``
and ``led_b`` stay separate. The ``Debug`` category below shows this.

.. sv:automodule:: ahb_arbiter
