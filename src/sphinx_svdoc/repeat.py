"""Collapse repeated ports into templates (``m<n>_haddr``, n = 0 … 7).

Two mechanisms:

* **Repeated bundles (explicit).**  A bundle whose comment contains a line
  ``:repeat:`` is a template.  The bundles that immediately follow it, in
  the same category, are merged into it when they are copies: same number
  of items, the same direction/type/default for each, and names (and title)
  differing from the template only by one index.  The index is a number
  (``m0``, ``m12``) or a single letter (``ma``, ``mB``).  The first bundle
  that isn't a copy ends the merge, and is documented normally.

* **Repeated ports outside bundles (automatic).**  Within a run of ports
  that are not in a bundle (categorised or not), ports whose names differ
  only by a number, with the same direction, type and description (the
  description may contain the same number), become one row.  Letters are
  not used here, so e.g. ``led_r``/``led_g``/``led_b`` stay separate.
"""
from __future__ import annotations

import re
from dataclasses import replace

from .model import Item, Module

PLACEHOLDER = "<n>"
REPEAT_RE = re.compile(r"^\s*:repeat:\s*$", re.IGNORECASE | re.MULTILINE)


# --------------------------------------------------------------------------
# Index arithmetic
# --------------------------------------------------------------------------
def _is_index(a: str, b: str, letters: bool) -> bool:
    if a.isdigit() and b.isdigit():
        return a != b
    if letters and len(a) == len(b) == 1 and a.isalpha() and b.isalpha():
        return a != b and a.islower() == b.islower()
    return False


def diff_index(a: str, b: str, letters: bool = True):
    """If *a* and *b* differ only by one index, return ``(pos, va, vb)``.

    *pos* is where the index starts in *a*; *va*/*vb* are the two values.
    Digit runs are taken whole, so ``m0_x`` / ``m10_x`` gives ``("0", "10")``.
    """
    if a == b:
        return None
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    j = 0
    while j < n - i and a[len(a) - 1 - j] == b[len(b) - 1 - j]:
        j += 1
    # widen to whole digit runs
    while i > 0 and a[i - 1].isdigit() and (i < len(a) - j or i < len(b) - j):
        i -= 1
    while j > 0 and a[len(a) - j].isdigit():
        j -= 1
    va, vb = a[i:len(a) - j], b[i:len(b) - j]
    if not _is_index(va, vb, letters):
        return None
    # A letter index must stand alone, not be the middle of a word
    if not va.isdigit():
        before = a[i - 1] if i else ""
        after = a[i + 1] if i + 1 < len(a) else ""
        if before.isalpha() and after.isalpha():
            return None
    return i, va, vb


def fmt_range(values: list[str]) -> str:
    """``0 … 7`` for a contiguous run of 3+, else a comma list."""
    if values and all(v.isdigit() for v in values):
        nums = [int(v) for v in values]
    elif values and all(len(v) == 1 and v.isalpha() for v in values):
        nums = [ord(v) for v in values]
    else:
        return ", ".join(values)
    contiguous = all(b - a == 1 for a, b in zip(nums, nums[1:]))
    if contiguous and len(values) >= 3:
        return f"{values[0]} … {values[-1]}"
    return ", ".join(values)


def _template(name: str, pos: int, value: str) -> str:
    return name[:pos] + PLACEHOLDER + name[pos + len(value):]


def _sub_doc(doc: str, value: str) -> str:
    return re.sub(rf"(?<![\w]){re.escape(value)}(?![\w])", PLACEHOLDER, doc)


# --------------------------------------------------------------------------
# Repeated bundles
# --------------------------------------------------------------------------
def _runs(items: list[Item]):
    """Split items into runs sharing the same (category, bundle)."""
    runs: list[tuple[tuple[str, str], list[Item]]] = []
    for it in items:
        key = (it.category, it.bundle)
        if runs and runs[-1][0] == key:
            runs[-1][1].append(it)
        else:
            runs.append((key, [it]))
    return runs


def _copy_index(tmpl_title, tmpl, title, items):
    """``(title_pos, title_va, va, vb)`` if (title, items) copies the template.

    *va*/*vb* are the index values in the port names; the title may spell
    the same index in a different case (``port A`` / ``sa_hsel``).
    """
    if len(items) != len(tmpl):
        return None
    va = vb = None
    for t, c in zip(tmpl, items):
        if (t.kind, t.type, t.default) != (c.kind, c.type, c.default):
            return None
        d = diff_index(t.name, c.name)
        if d is None:
            return None
        if va is None:
            va, vb = d[1], d[2]
        elif (d[1], d[2]) != (va, vb):
            return None
    if title == tmpl_title:
        return None, None, va, vb
    d = diff_index(tmpl_title, title)
    if d is None or (d[1].lower(), d[2].lower()) != (va.lower(), vb.lower()):
        return None
    return d[0], d[1], va, vb


def take_repeat_markers(mod: Module) -> set[str]:
    """Remove ``:repeat:`` lines from bundle descriptions; return marked titles."""
    marked = {t for t, desc in mod.bundle_docs.items() if REPEAT_RE.search(desc)}
    for t in marked:
        desc = REPEAT_RE.sub("", mod.bundle_docs[t]).strip("\n")
        desc = re.sub(r"\n{3,}", "\n\n", desc)
        if desc:
            mod.bundle_docs[t] = desc
        else:
            del mod.bundle_docs[t]
    return marked


def collapse_bundles(items: list[Item], mod: Module, marked: set[str]) -> list[Item]:
    """Merge the copies that follow a ``:repeat:`` bundle into it.

    Copies must immediately follow the template, in the same category.
    """
    if not marked:
        return items
    runs = _runs(items)
    out: list[Item] = []
    i = 0
    while i < len(runs):
        (cat, title), tmpl = runs[i]
        i += 1
        if not title or title not in marked:
            out += tmpl
            continue
        values, title_pos, title_va, item_pos = [], None, None, None
        while i < len(runs):
            (ccat, ctitle), citems = runs[i]
            if ccat != cat or not ctitle:
                break
            idx = _copy_index(title, tmpl, ctitle, citems)
            if idx is None or (values and idx[2] != values[0]) or idx[3] in values:
                break
            if not values:
                values = [idx[2]]
                title_pos, title_va = idx[0], idx[1]
                item_pos = [diff_index(t.name, c.name)[0] for t, c in zip(tmpl, citems)]
            values.append(idx[3])
            i += 1
        if not values:
            out += tmpl             # nothing to merge
            continue
        va = values[0]
        new_title = (_template(title, title_pos, title_va) if title_pos is not None
                     else title)
        if new_title != title and title in mod.bundle_docs:
            mod.bundle_docs[new_title] = mod.bundle_docs.pop(title)
        mod.bundle_repeat[new_title] = values
        for it, pos in zip(tmpl, item_pos):
            out.append(replace(it, name=_template(it.name, pos, va),
                               doc=_sub_doc(it.doc, va), bundle=new_title))
    return out


# --------------------------------------------------------------------------
# Repeated ports outside bundles
# --------------------------------------------------------------------------
def _candidates(it: Item):
    for m in re.finditer(r"\d+", it.name):
        v = m.group()
        yield (_template(it.name, m.start(), v), it.kind, it.type,
               _sub_doc(it.doc, v), it.hidden), v


def collapse_rows(items: list[Item]) -> list[Item]:
    out: list[Item] = []
    for (_cat, bundle), run in _runs(items):
        if bundle:
            out += run
            continue
        counts: dict = {}
        for it in run:
            for key, v in _candidates(it):
                counts.setdefault(key, set()).add(v)
        chosen: dict = {}         # key -> collapsed Item (placed at first member)
        for it in run:
            best = max(((len(counts[k]), k, v) for k, v in _candidates(it)),
                       default=None, key=lambda x: x[0])
            if best is None or best[0] < 2:
                out.append(it)
                continue
            _, key, v = best
            if key not in chosen:
                chosen[key] = replace(it, name=key[0], doc=key[3], indices=[])
                out.append(chosen[key])
            if v not in chosen[key].indices:
                chosen[key].indices.append(v)
    return out


def collapse_repeats(mod: Module):
    marked = take_repeat_markers(mod)
    mod.params = collapse_bundles(mod.params, mod, marked)
    mod.ports = collapse_rows(collapse_bundles(mod.ports, mod, marked))
