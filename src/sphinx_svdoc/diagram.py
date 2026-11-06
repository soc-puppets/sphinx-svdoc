"""Module interface diagrams (a "symbol": a box with one wire per connection).

* Each **bundle** is drawn as a single connection labelled with its title.
  Every other port gets a wire of its own, labelled with name and width.
* Arrows show direction: into the box (all inputs), out of it (all outputs),
  or both ways (a mix, or any ``inout``/interface port).
* Inputs are drawn on the left, outputs on the right.  A two-way connection
  goes on the side of its majority direction (inputs win ties).
* **Categories** are not drawn as such; the wires of each category are kept
  together, with extra space between categories.
* Buses (bundles and multi-bit ports) are drawn thick.
* Overridable parameters are listed inside the box (header localparams are
  derived constants and are left out).  Hidden (``:nodoc:``) items are left
  out; repeated bundles and collapsed ports show their index range.

The layout is computed here and pinned (``neato`` with fixed positions), so
wires are straight and labels line up.  Graphviz right/left-aligns the
labels itself, so only a generous width estimate is needed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .model import Module
from .repeat import fmt_range

PITCH = 22.0      # vertical distance between wires (pt)
WIRE = 56.0       # wire length (pt)
GAP = 5.0         # wire end to label (pt)
PAD = 14.0        # padding inside the box (pt)
CAT_GAP = 12.0    # extra space between categories (pt)


@dataclass
class Connection:
    label: str
    direction: str    # 'in' | 'out' | 'both'
    bus: bool
    side: str         # 'L' | 'R'
    category: str = ""


def _dims(typ: str) -> str:
    m = re.search(r"(\[.*\])", typ or "")
    return m.group(1).replace(" ", "") if m else ""


def connections(mod: Module) -> list[Connection]:
    """Wires to draw, in source order."""
    acc: list[list] = []          # [label, kinds, bus, balance, category]
    by_bundle: dict[tuple[str, str], list] = {}
    for p in mod.doc_ports:
        k = {"input": "in", "output": "out"}.get(p.kind, "both")
        if p.bundle:
            key = (p.category, p.bundle)
            c = by_bundle.get(key)
            if c is None:
                label = p.bundle
                if p.bundle in mod.bundle_repeat:
                    label += f" (n = {fmt_range(mod.bundle_repeat[p.bundle])})"
                c = by_bundle[key] = [label, set(), True, 0, p.category]
                acc.append(c)
        else:
            label = p.name + _dims(p.type)
            if p.indices:
                label += f" (n = {fmt_range(p.indices)})"
            c = [label, set(), bool(_dims(p.type)) or "interface" in p.kind, 0, p.category]
            acc.append(c)
        c[1].add(k)
        c[3] += {"in": 1, "out": -1}.get(k, 0)
    out = []
    for label, kinds, bus, balance, category in acc:
        d = next(iter(kinds)) if len(kinds) == 1 else "both"
        side = "L" if d == "in" or (d == "both" and balance >= 0) else "R"
        out.append(Connection(label, d, bus, side, category))
    return out


def _offsets(items: list[Connection]) -> tuple[list[float], float]:
    """Vertical offset (from the top) of each wire, and the total height."""
    ys, y, prev = [], 0.0, None
    for c in items:
        if prev is not None and c.category != prev:
            y += CAT_GAP
        ys.append(y + PITCH / 2)
        y += PITCH
        prev = c.category
    return ys, y


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def _est_width(s: str, size: float = 10) -> float:
    # Deliberately generous; the label cell is right/left aligned by Graphviz,
    # so overestimating only adds blank margin at the outer edge.
    return len(s) * 0.62 * size + 4


def interface_dot(mod: Module) -> str:
    """Graphviz source (``layout=neato``, pinned positions) for *mod*."""
    conns = connections(mod)
    left = [c for c in conns if c.side == "L"]
    right = [c for c in conns if c.side == "R"]
    params = [f"{p.name} = {p.default}" if p.default else p.name
              for p in mod.doc_params if p.kind != "localparam"]

    ly, lh = _offsets(left)
    ry, rh = _offsets(right)
    box_h = max(max(lh, rh, PITCH) + PAD, (1 + len(params)) * 13 + 2 * PAD)
    box_w = max(130.0, _est_width(mod.name, 11) + 2 * PAD,
                *(_est_width(p, 9) + 2 * PAD for p in params))
    lw = max([_est_width(c.label) for c in left] or [0.0])
    rw = max([_est_width(c.label) for c in right] or [0.0])
    x0 = lw + GAP + WIRE
    x1 = x0 + box_w
    inch = lambda v: f"{v / 72:.4f}"
    pos = lambda x, y: f'pos="{inch(x)},{inch(y)}!"'

    g = ["digraph svdoc_interface {",
         "  layout=neato; splines=false; outputorder=edgesfirst; pad=0.1;",
         '  node [fontname="sans-serif", fontsize=10];',
         '  edge [arrowsize=0.7, color="#333333"];']
    plabel = "".join(f'<BR/><FONT POINT-SIZE="9">{_esc(p)}</FONT>' for p in params)
    g.append(f'  box [shape=box, style=filled, fillcolor="#f4f6fa", color="#333333", '
             f'penwidth=1.5, fixedsize=true, width={inch(box_w)}, height={inch(box_h)}, '
             f'{pos((x0 + x1) / 2, box_h / 2)}, label=<<B>{_esc(mod.name)}</B>{plabel}>];')

    def side(items, is_left):
        width = lw if is_left else rw
        offsets = ly if is_left else ry
        for i, c in enumerate(items):
            y = box_h - PAD / 2 - offsets[i]
            xb = x0 if is_left else x1
            xe = xb - WIRE if is_left else xb + WIRE
            xl = xe - GAP - width / 2 if is_left else xe + GAP + width / 2
            s = "l" if is_left else "r"
            align = "RIGHT" if is_left else "LEFT"
            g.append(f"  {s}b{i} [shape=point, width=0.01, style=invis, {pos(xb, y)}];")
            g.append(f"  {s}e{i} [shape=point, width=0.01, style=invis, {pos(xe, y)}];")
            g.append(f'  {s}t{i} [shape=plaintext, margin=0, {pos(xl, y)}, label=<'
                     f'<TABLE BORDER="0" CELLBORDER="0" CELLPADDING="0" CELLSPACING="0">'
                     f'<TR><TD FIXEDSIZE="TRUE" WIDTH="{width:.0f}" HEIGHT="14" '
                     f'ALIGN="{align}">{_esc(c.label)}</TD></TR></TABLE>>];')
            attrs = f"penwidth={2.6 if c.bus else 1.1}"
            if c.direction == "both":
                attrs += ", dir=both"
            # Left wires are inputs (into the box), right wires outputs; two-way
            # wires get both arrowheads via dir=both.
            edge = f"{s}e{i} -> {s}b{i}" if is_left else f"{s}b{i} -> {s}e{i}"
            g.append(f"  {edge} [{attrs}];")

    side(left, True)
    side(right, False)
    g.append("}")
    return "\n".join(g)
