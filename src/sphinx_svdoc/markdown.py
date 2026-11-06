"""Markdown output (kept for quick previews / GitHub & GitLab rendering)."""
from __future__ import annotations

from .model import Module
from .repeat import fmt_range


def name_md(i) -> str:
    return f"`{i.name}` (n = {fmt_range(i.indices)})" if i.indices else f"`{i.name}`"


def md_esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", "<br>")


def code(s: str) -> str:
    return f"`{s}`" if s else ""


def table(items, cols):
    """cols: list of (header, fn(item))."""
    lines = ["| " + " | ".join(h for h, _ in cols) + " |",
             "|" + "|".join("---" for _ in cols) + "|"]
    for it in items:
        lines.append("| " + " | ".join(md_esc(fn(it)) for _, fn in cols) + " |")
    return lines


def _runs(items, key):
    runs = []
    for it in items:
        if runs and runs[-1][0] == key(it):
            runs[-1][1].append(it)
        else:
            runs.append((key(it), [it]))
    return runs


def structured_table(items, cols, mod: Module):
    """Tables laid out by category (#### heading) and bundle (bold heading)."""
    out = []
    for category, run in _runs(items, lambda i: i.category):
        if category:
            out += ["", f"#### {category}", ""]
            if category in mod.category_docs:
                out += [mod.category_docs[category], ""]
        for bundle, its in _runs(run, lambda i: i.bundle):
            if bundle:
                reps = mod.bundle_repeat.get(bundle)
                out += ["", f"**{bundle}**" + (f" (n = {fmt_range(reps)})" if reps else ""), ""]
                if bundle in mod.bundle_docs:
                    out += [mod.bundle_docs[bundle], ""]
            out += table(its, cols)
    return out


def render_module(mod: Module, rel_src: str, known: set[str],
                  include_locals: bool = False, include_instances: bool = False) -> str:
    L = [f"# Module `{mod.name}`", ""]
    if mod.summary:
        L += [f"*{mod.summary}*", ""]
    L += [f"**Source:** [`{rel_src}`]({rel_src}#L{mod.line}) (line {mod.line})", ""]
    if mod.body:
        L += [mod.body, ""]
    if mod.doc_params:
        L += ["## Parameters", ""]
        L += structured_table(mod.doc_params, [
            ("Name", lambda i: code(i.name)),
            ("Type", lambda i: code(i.type) + (" (localparam)" if i.kind == "localparam" else "")),
            ("Default", lambda i: code(i.default)), ("Description", lambda i: i.doc)], mod)
        L.append("")
    if mod.doc_ports:
        L += ["## Ports", ""]
        L += structured_table(mod.doc_ports, [
            ("Name", name_md), ("Dir", lambda i: i.kind),
            ("Type", lambda i: code(i.type)), ("Description", lambda i: i.doc)], mod)
        L.append("")
    lp = mod.localparams if include_locals else []
    td = mod.typedefs if include_locals else []
    if lp:
        L += ["## Local parameters", ""]
        L += structured_table(lp, [("Name", lambda i: code(i.name)),
                                ("Value", lambda i: code(i.default)),
                                ("Description", lambda i: i.doc)], mod)
        L.append("")
    if td:
        L += ["## Types", ""]
        L += table(td, [("Name", lambda i: code(i.name)), ("Definition", lambda i: code(i.type)),
                        ("Description", lambda i: i.doc)])
        L.append("")
    if include_instances and mod.instances:
        L += ["## Instances", ""]
        L += table(mod.instances, [
            ("Instance", lambda i: code(i.name)),
            ("Module", lambda i: f"[`{i.module}`]({i.module}.md)" if i.module in known
             else code(i.module))])
        L.append("")
    return "\n".join(L)


def render_index(mods: list[Module], title: str) -> str:
    known = {m.name for m in mods}
    used = {i.module for m in mods for i in m.instances}
    L = [f"# {title}", "", "## Modules", "",
         "| Module | Description |", "|---|---|"]
    for m in sorted(mods, key=lambda m: m.name):
        L.append(f"| [`{m.name}`]({m.name}.md) | {md_esc(m.summary)} |")
    edges = [(m.name, i.module, i.name) for m in mods for i in m.instances]
    if edges:
        L += ["", "## Hierarchy", "", "```mermaid", "graph TD"]
        for parent, child, inst in edges:
            style = "" if child in known else ":::ext"
            L.append(f"  {parent} -->|{inst}| {child}{style}")
        L.append("  classDef ext stroke-dasharray: 4 3")
        L += ["```", ""]
        tops = sorted(known - used)
        if tops:
            L.append("Top-level: " + ", ".join(f"[`{t}`]({t}.md)" for t in tops))
    return "\n".join(L) + "\n"
