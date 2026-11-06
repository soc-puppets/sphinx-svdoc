"""Render :class:`~sphinx_svdoc.model.Module` objects as reStructuredText.

Two flavours:

* ``domain=True`` (used by the Sphinx extension): wraps each module in an
  ``.. sv:module::`` directive and cross-references with ``:sv:mod:``.
* ``domain=False`` (offline CLI output): plain docutils RST with a section
  title per module, so the output also works without the extension.

The header-comment body is reStructuredText and is passed through verbatim.
Inline (port / parameter) comments are treated as plain text and escaped,
except that ````double-backtick```` literals are kept.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .model import Item, Module
from .repeat import fmt_range

INDENT = "   "


# --------------------------------------------------------------------------
# Inline helpers
# --------------------------------------------------------------------------
_ESCAPE_RE = re.compile(r"([\\*`|_\[\]])")
_LIST_START_RE = re.compile(r"^([-*+]|\d+[.)]|#[.)]|\(\d+\))\s")


def text(s: str) -> str:
    """Escape plain comment text for use in a table cell or paragraph."""
    if not s:
        return ""
    parts = re.split(r"(``[^`]+``)", s)
    out = "".join(p if p.startswith("``") and p.endswith("``") and len(p) > 4
                  else _ESCAPE_RE.sub(r"\\\1", p) for p in parts)
    if _LIST_START_RE.match(out):
        out = "\\" + out
    return out


def lit(s: str) -> str:
    """Inline literal that survives backticks / surrounding whitespace."""
    if not s:
        return ""
    if "`" in s or s != s.strip() or "\\" in s:
        return ":code:`" + s.replace("\\", "\\\\").replace("`", "\\`") + "`"
    return f"``{s}``"


def name_cell(item) -> str:
    """Item name; collapsed rows also give their index range."""
    if item.indices:
        return f"{lit(item.name)} (n = {fmt_range(item.indices)})"
    return lit(item.name)


def modref(name: str, known: set[str], domain: bool) -> str:
    if domain and name in known:
        return f":sv:mod:`{name}`"
    return lit(name)


# --------------------------------------------------------------------------
# File paths in the header body
# --------------------------------------------------------------------------
#: Directives whose argument is a file path.  ``drawio-*``/``wavedrom``/
#: ``plantuml`` come from third-party Sphinx extensions; listing them is
#: harmless when those extensions aren't installed.
PATH_DIRECTIVES = ("image", "figure", "include", "literalinclude", "graphviz",
                   "wavedrom", "plantuml", "drawio-image", "drawio-figure",
                   "kroki", "csv-table", "raw")
#: Options whose value is a file path (``.. csv-table:: :file:`` etc.)
PATH_OPTIONS = ("file",)

_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://|^data:")


def rebase_paths(body: str, from_dir, to_dir, directives=PATH_DIRECTIVES) -> str:
    """Rewrite relative file paths in *body* from *from_dir* to *to_dir*.

    Header comments refer to files (images, diagrams, includes) relative to
    the SV source file, but Sphinx resolves them relative to the document
    that contains the ``sv:automodule`` directive.  Absolute paths
    (``/...``, which Sphinx takes as source-dir relative) and URLs are kept.
    """
    import os
    names = "|".join(re.escape(d) for d in directives)
    dir_re = re.compile(rf"^(\s*\.\.\s+(?:{names})::\s+)(\S.*?)\s*$")
    opt_re = re.compile(rf"^(\s+:(?:{'|'.join(PATH_OPTIONS)}):\s+)(\S.*?)\s*$")

    def fix(path: str) -> str:
        if path.startswith("/") or _URL_RE.match(path) or "<" in path:
            return path            # absolute, URL, or <stdlib include>
        target = os.path.normpath(os.path.join(from_dir, path))
        return os.path.relpath(target, to_dir).replace(os.sep, "/")

    out = []
    for line in body.splitlines():
        m = dir_re.match(line) or opt_re.match(line)
        out.append(m.group(1) + fix(m.group(2)) if m else line)
    return "\n".join(out)


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------
def list_table(rows: list[list[str]], header: list[str], title: str = "",
               cls: str = "") -> list[str]:
    L = [f".. list-table:: {text(title)}".rstrip(),
         "   :header-rows: 1",
         "   :widths: auto"]
    if cls:
        L.append(f"   :class: {cls}")
    L.append("")
    for row in [header] + rows:
        for j, cell in enumerate(row):
            cell = cell.replace("\n", " ")
            L.append(f"   {'* -' if j == 0 else '  -'} {cell}".rstrip())
    L.append("")
    return L


def indent(lines: list[str], pad: str = INDENT) -> list[str]:
    return [(pad + l) if l else "" for l in lines]


def _runs(items: list[Item], key):
    runs: list[tuple[str, list[Item]]] = []
    for it in items:
        k = key(it)
        if runs and runs[-1][0] == k:
            runs[-1][1].append(it)
        else:
            runs.append((k, [it]))
    return runs


def _titled_block(cls: str, heading: str, desc: str, body: list[str], rebase) -> list[str]:
    inner = [".. rubric:: " + heading, f"   :class: {cls}-title", ""]
    if desc:
        inner += rebase(desc).splitlines() + [""]
    inner += body
    return [f".. container:: {cls}", ""] + indent(inner) + [""]


def structured_tables(items: list[Item], header, row_fn, cls, mod: Module,
                      rebase=lambda s: s) -> list[str]:
    """Tables for *items*, laid out by category and bundle.

    A category is a ``svdoc-category`` container: heading, description, then
    its contents.  Inside it, ports outside any bundle form plain tables and
    each bundle is a ``svdoc-bundle`` container (heading with any repeat
    range, description, table).
    """
    def contents(its):
        L = []
        for bundle, run in _runs(its, lambda i: i.bundle):
            table = list_table([row_fn(i) for i in run], header, cls=cls)
            if not bundle:
                L += table
                continue
            heading = text(bundle)
            if bundle in mod.bundle_repeat:
                heading += f" (n = {fmt_range(mod.bundle_repeat[bundle])})"
            L += _titled_block("svdoc-bundle", heading, mod.bundle_docs.get(bundle, ""),
                               table, rebase)
        return L

    L = []
    for category, run in _runs(items, lambda i: i.category):
        if not category:
            L += contents(run)
        else:
            L += _titled_block("svdoc-category", text(category),
                               mod.category_docs.get(category, ""), contents(run), rebase)
    return L


def param_type(item: Item) -> str:
    """Type cell; header localparams are marked as not overridable."""
    t = lit(item.type)
    if item.kind == "localparam":
        t = (t + " " if t else "") + "(localparam)"
    return t


# --------------------------------------------------------------------------
# Module
# --------------------------------------------------------------------------
def render_module(mod: Module, *, known: Iterable[str] = (), domain: bool = True,
                  source: str | None = None, source_url: str | None = None,
                  include_locals: bool = False,
                  include_instances: bool = False,
                  diagram: bool = False,
                  no_index: bool = False,
                  doc_dir: str | None = None) -> list[str]:
    """Return RST lines documenting *mod*.

    By default only the module's interface is documented (black-box view):
    header comment, parameters and ports.  *include_locals* adds localparams
    and typedefs; *include_instances* adds the submodule instance table.
    *diagram* adds an interface diagram (needs ``sphinx.ext.graphviz``).

    *doc_dir* is the directory of the document the output will be parsed in;
    relative file paths in the header body are rebased from the SV file's
    directory to it.
    """
    known = set(known)
    sv_dir = Path(mod.file).resolve().parent
    rebase = ((lambda t: rebase_paths(t, sv_dir, doc_dir)) if doc_dir is not None
              else (lambda t: t))
    B: list[str] = []          # body lines (indented under the directive later)

    if mod.summary:
        B += [mod.summary, ""]
    if mod.body:
        B += rebase(mod.body).splitlines() + [""]
    src = source or str(mod.file)
    if source_url:
        B += [f":Source: `{src} <{source_url}>`__, line {mod.line}", ""]
    else:
        B += [f":Source: {lit(src)}, line {mod.line}", ""]
    if diagram and mod.doc_ports:
        B += render_interface(mod)

    if mod.doc_params:
        B += [".. rubric:: Parameters", ""]
        B += structured_tables(
            mod.doc_params, ["Name", "Type", "Default", "Description"],
            lambda i: [name_cell(i), param_type(i), lit(i.default), text(i.doc)],
            "svdoc-params", mod, rebase)
    if mod.doc_ports:
        B += [".. rubric:: Ports", ""]
        B += structured_tables(
            mod.doc_ports, ["Name", "Direction", "Type", "Description"],
            lambda i: [name_cell(i), text(i.kind), lit(i.type), text(i.doc)],
            "svdoc-ports", mod, rebase)
    if include_locals and mod.localparams:
        B += [".. rubric:: Local parameters", ""]
        B += structured_tables(
            mod.localparams, ["Name", "Value", "Description"],
            lambda i: [lit(i.name), lit(i.default), text(i.doc)],
            "svdoc-localparams", mod, rebase)
    if include_locals and mod.typedefs:
        B += [".. rubric:: Types", ""]
        B += list_table([[lit(i.name), lit(i.type), text(i.doc)]
                         for i in mod.typedefs],
                        ["Name", "Definition", "Description"], cls="svdoc-types")
    if include_instances and mod.instances:
        B += [".. rubric:: Instances", ""]
        B += list_table([[lit(i.name), modref(i.module, known, domain)]
                         for i in mod.instances],
                        ["Instance", "Module"], cls="svdoc-instances")

    if domain:
        L = [f".. sv:module:: {mod.name}"]
        if mod.keyword != "module":
            L.append(f"   :keyword: {mod.keyword}")
        if no_index:
            L.append("   :no-index:")
        L.append("")
        L += indent(B)
        return L
    title = f"{mod.keyword} ``{mod.name}``"
    return [title, "=" * len(title), ""] + B


def render_interface(mod: Module) -> list[str]:
    """``.. graphviz::`` block drawing the module's interface."""
    from .diagram import interface_dot
    return ([".. graphviz::", "   :align: center", "   :class: svdoc-interface",
             f"   :alt: Interface of {mod.name}", ""]
            + indent(interface_dot(mod).splitlines()) + [""])


# --------------------------------------------------------------------------
# Hierarchy
# --------------------------------------------------------------------------
def _edges(mods: list[Module], top: str | None):
    by_name = {m.name: m for m in mods}
    edges: dict[tuple[str, str], list[str]] = {}
    for m in mods:
        for inst in m.instances:
            edges.setdefault((m.name, inst.module), []).append(inst.name)
    if top:
        keep, todo = set(), [top]
        while todo:
            n = todo.pop()
            if n in keep:
                continue
            keep.add(n)
            if n in by_name:
                todo += [i.module for i in by_name[n].instances]
        edges = {k: v for k, v in edges.items() if k[0] in keep}
        nodes = keep
    else:
        nodes = set(by_name) | {c for _, c in edges}
    return by_name, edges, nodes


def _label(names: list[str]) -> str:
    return "\\n".join(names[:3] + ([f"+{len(names) - 3} more"] if len(names) > 3 else []))


def render_hierarchy(mods: list[Module], *, style: str = "graphviz",
                     top: str | None = None, domain: bool = True) -> list[str]:
    by_name, edges, nodes = _edges(mods, top)
    if not nodes:
        return []
    if style == "graphviz":
        L = [".. graphviz::", "   :align: center", "",
             "   digraph svdoc_hierarchy {",
             "      rankdir=LR;",
             '      node [shape=box, style="rounded", fontname="sans-serif", fontsize=10];',
             '      edge [fontname="sans-serif", fontsize=8, color="#666666"];']
        for n in sorted(nodes):
            attrs = 'style="rounded,dashed", fontcolor="#666666"' if n not in by_name else ""
            L.append(f'      "{n}" [{attrs}];' if attrs else f'      "{n}";')
        for (parent, child), insts in edges.items():
            L.append(f'      "{parent}" -> "{child}" [label="{_label(insts)}"];')
        L += ["   }", ""]
        return L

    # Nested bullet list
    children: dict[str, list[tuple[str, str]]] = {}
    for (parent, child), insts in edges.items():
        children.setdefault(parent, []).extend((i, child) for i in insts)
    instantiated = {c for _, c in edges}
    roots = [top] if top else sorted(n for n in nodes if n not in instantiated) or sorted(nodes)
    known = set(by_name)
    L: list[str] = []

    def emit(name, depth, inst=None, seen=()):
        pad = "  " * depth
        label = modref(name, known, domain)
        L.append(f"{pad}- {lit(inst) + ': ' if inst else ''}{label}")
        if name in seen:
            return                       # recursion guard
        kids = children.get(name, [])
        if kids:
            L.append("")
            for i, c in kids:
                emit(c, depth + 1, i, seen + (name,))
            L.append("")

    for r in roots:
        emit(r, 0)
    L.append("")
    # collapse runs of blank lines
    out = []
    for l in L:
        if l or (out and out[-1]):
            out.append(l)
    return out + [""]


def render_index(mods: list[Module], title: str) -> list[str]:
    """Offline (plain docutils / Sphinx without the extension) index page."""
    L = [title, "=" * len(title), ""]
    rows = [[f":doc:`{m.name}`", text(m.summary)] for m in sorted(mods, key=lambda m: m.name)]
    L += list_table(rows, ["Module", "Description"])
    hier = render_hierarchy(mods, style="list", domain=False)
    if any(m.instances for m in mods):
        L += ["Hierarchy", "---------", ""] + hier
    L += [".. toctree::", "   :hidden:", ""]
    L += [f"   {m.name}" for m in sorted(mods, key=lambda m: m.name)] + [""]
    return L
