"""Sphinx extension: document SystemVerilog modules straight from source.

conf.py::

    extensions = ["sphinx_svdoc", "sphinx.ext.graphviz"]
    svdoc_sources = ["../src/rtl/*.sv"]        # globs, relative to conf.py

Directives (all in the ``sv`` domain)::

    .. sv:automodule:: csr          document one module from source
    .. sv:autoall::                 document every module (optional fnmatch pattern)
    .. sv:hierarchy:: [top]         instance hierarchy (Graphviz or nested list)
    .. sv:module:: name             hand-written module description

Role: ``:sv:mod:`csr``` links to a documented module.
"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_refnode

from . import __version__
from .model import Module
from .parser import collect_files, parse_file
from .rst import render_hierarchy, render_interface, render_module

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Source loading
# --------------------------------------------------------------------------
def load_sources(app):
    """builder-inited: parse every file in ``svdoc_sources``."""
    cfg = app.config
    patterns = [p if os.path.isabs(p) else os.path.join(app.confdir, p)
                for p in cfg.svdoc_sources]
    files = collect_files(patterns, recursive=True)
    if cfg.svdoc_sources and not files:
        logger.warning("sphinx-svdoc: svdoc_sources %r matched no files", cfg.svdoc_sources)
    mods: dict[str, Module] = {}
    for f in files:
        for m in parse_file(f, warn=lambda msg: logger.warning("sphinx-svdoc: %s", msg)):
            if m.name in mods:
                logger.warning("sphinx-svdoc: module %s defined in both %s and %s; using the first",
                               m.name, mods[m.name].file, m.file)
                continue
            mods[m.name] = m
    # Stored on the environment (not the app) so directives can reach it.
    app.env.svdoc_modules = mods
    app.env.svdoc_sources = {name: source_info(app, m) for name, m in mods.items()}
    logger.info("sphinx-svdoc: %d module(s) from %d file(s)", len(mods), len(files))


def source_info(app, mod: Module) -> tuple[str, str | None]:
    root = app.config.svdoc_source_root
    root = Path(app.confdir, root) if root else Path(app.confdir).parent
    try:
        rel = os.path.relpath(Path(mod.file).resolve(), root.resolve())
    except ValueError:          # different drive on Windows
        rel = str(mod.file)
    rel = rel.replace(os.sep, "/")
    url = None
    if app.config.svdoc_source_url:
        url = app.config.svdoc_source_url.format(path=rel, line=mod.line)
    return rel, url


class _SvdocDirective(SphinxDirective):
    """Helpers shared by the auto directives."""

    @property
    def modules(self) -> dict[str, Module]:
        return getattr(self.env, "svdoc_modules", {})

    def parse_lines(self, lines: list[str], source: str) -> list[nodes.Node]:
        container = nodes.container()
        self.state.nested_parse(StringList(lines, source=source),
                                self.content_offset, container)
        return container.children

    def show(self, what: str) -> bool:
        """``:<what>:`` / ``:no-<what>:`` option, else the conf.py default."""
        if what in self.options:
            return True
        if f"no-{what}" in self.options:
            return False
        return getattr(self.config, f"svdoc_show_{what}")

    def graphviz_loaded(self) -> bool:
        if "sphinx.ext.graphviz" in self.config.extensions:
            return True
        logger.info("sphinx-svdoc: sphinx.ext.graphviz not loaded; skipping interface diagrams",
                    once=True)
        return False

    def render(self, mod: Module) -> list[nodes.Node]:
        self.env.note_dependency(str(Path(mod.file).resolve()))
        src, url = self.env.svdoc_sources[mod.name]
        lines = render_module(mod, known=self.modules.keys(), domain=True,
                              source=src, source_url=url,
                              include_locals=self.show("locals"),
                              include_instances=self.show("instances"),
                              diagram=self.show("diagram") and self.graphviz_loaded(),
                              no_index="no-index" in self.options,
                              doc_dir=str(Path(self.env.doc2path(self.env.docname)).resolve().parent))
        return self.parse_lines(lines, f"{mod.file} [sphinx-svdoc]")


VISIBILITY_OPTIONS = {opt: directives.flag for what in ("locals", "instances", "diagram")
                      for opt in (what, f"no-{what}")}
VISIBILITY_OPTIONS["no-index"] = directives.flag   # document again without a target


class AutoModuleDirective(_SvdocDirective):
    required_arguments = 1
    option_spec = dict(VISIBILITY_OPTIONS)

    def run(self):
        name = self.arguments[0]
        mod = self.modules.get(name)
        if mod is None:
            logger.warning("sphinx-svdoc: unknown module %r (is it in svdoc_sources?)", name,
                           location=self.get_location())
            return []
        return self.render(mod)


class AutoAllDirective(_SvdocDirective):
    optional_arguments = 1
    option_spec = {**VISIBILITY_OPTIONS, "exclude": directives.unchanged}

    def run(self):
        pattern = self.arguments[0] if self.arguments else "*"
        exclude = (self.options.get("exclude") or "").split()
        out = []
        for name in sorted(self.modules):
            if fnmatch.fnmatch(name, pattern) and not any(fnmatch.fnmatch(name, e) for e in exclude):
                out += self.render(self.modules[name])
        return out


class InterfaceDirective(_SvdocDirective):
    """``.. sv:interface:: name`` - just the interface diagram of a module."""
    required_arguments = 1

    def run(self):
        mod = self.modules.get(self.arguments[0])
        if mod is None:
            logger.warning("sphinx-svdoc: unknown module %r", self.arguments[0],
                           location=self.get_location())
            return []
        if not self.graphviz_loaded():
            return []
        self.env.note_dependency(str(Path(mod.file).resolve()))
        return self.parse_lines(render_interface(mod), f"{mod.file} [sphinx-svdoc interface]")


class HierarchyDirective(_SvdocDirective):
    optional_arguments = 1
    option_spec = {"style": lambda a: directives.choice(a, ("graphviz", "list"))}

    def run(self):
        top = self.arguments[0] if self.arguments else None
        mods = list(self.modules.values())
        if top and top not in self.modules:
            logger.warning("sphinx-svdoc: unknown top module %r", top, location=self.get_location())
            return []
        for m in mods:
            self.env.note_dependency(str(Path(m.file).resolve()))
        style = self.options.get("style", self.config.svdoc_hierarchy)
        if style == "graphviz" and "sphinx.ext.graphviz" not in self.config.extensions:
            logger.info("sphinx-svdoc: sphinx.ext.graphviz not loaded; drawing hierarchy as a list")
            style = "list"
        lines = render_hierarchy(mods, style=style, top=top, domain=True)
        return self.parse_lines(lines, "[sphinx-svdoc hierarchy]")


# --------------------------------------------------------------------------
# Domain
# --------------------------------------------------------------------------
class SVModuleDirective(ObjectDescription):
    has_content = True
    required_arguments = 1
    option_spec = {"keyword": directives.unchanged, "no-index": directives.flag,
                   "noindex": directives.flag}

    def handle_signature(self, sig, signode):
        name = sig.strip()
        kw = self.options.get("keyword", "module")
        signode += addnodes.desc_annotation(kw + " ", kw + " ")
        signode += addnodes.desc_name(name, name)
        signode["_toc_parts"] = (name,)
        return name

    def add_target_and_index(self, name, sig, signode):
        node_id = f"sv-module-{nodes.make_id(name)}"
        signode["ids"].append(node_id)
        self.env.get_domain("sv").note_module(name, node_id, self.get_location())
        kw = self.options.get("keyword", "module")
        self.indexnode["entries"].append(
            ("single", f"{name} (SystemVerilog {kw})", node_id, "", None))

    def _object_hierarchy_parts(self, sig_node):
        return sig_node.get("_toc_parts", ())

    def _toc_entry_name(self, sig_node):
        parts = sig_node.get("_toc_parts")
        return parts[-1] if parts else ""


class SVDomain(Domain):
    name = "sv"
    label = "SystemVerilog"
    object_types = {"module": ObjType("module", "mod")}
    directives = {
        "module": SVModuleDirective,
        "automodule": AutoModuleDirective,
        "autoall": AutoAllDirective,
        "hierarchy": HierarchyDirective,
        "interface": InterfaceDirective,
    }
    roles = {"mod": XRefRole()}
    initial_data = {"modules": {}}      # name -> (docname, node_id)

    def note_module(self, name, node_id, location=None):
        mods = self.data["modules"]
        if name in mods and mods[name][0] != self.env.docname:
            logger.warning("sphinx-svdoc: module %s already documented in %s", name,
                           mods[name][0], location=location)
        mods[name] = (self.env.docname, node_id)

    def clear_doc(self, docname):
        for name, (doc, _) in list(self.data["modules"].items()):
            if doc == docname:
                del self.data["modules"][name]

    def merge_domaindata(self, docnames, otherdata):
        for name, (doc, nid) in otherdata["modules"].items():
            if doc in docnames:
                self.data["modules"][name] = (doc, nid)

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        entry = self.data["modules"].get(target)
        if entry is None:
            return None
        return make_refnode(builder, fromdocname, entry[0], entry[1], contnode, target)

    def resolve_any_xref(self, env, fromdocname, builder, target, node, contnode):
        ref = self.resolve_xref(env, fromdocname, builder, "mod", target, node, contnode)
        return [("sv:mod", ref)] if ref else []

    def get_objects(self):
        for name, (doc, nid) in self.data["modules"].items():
            yield name, name, "module", doc, nid, 1


STATIC_DIR = Path(__file__).parent / "static"


def add_static_path(app):
    if app.builder.format == "html":
        app.config.html_static_path.append(str(STATIC_DIR))


def setup(app):
    app.add_config_value("svdoc_sources", [], "env", [list])
    app.add_config_value("svdoc_hierarchy", "graphviz", "env", [str])
    # Black-box by default: internals are opt-in
    app.add_config_value("svdoc_show_locals", False, "env", [bool])
    app.add_config_value("svdoc_show_instances", False, "env", [bool])
    app.add_config_value("svdoc_show_diagram", True, "env", [bool])  # interface, so on
    app.add_config_value("svdoc_source_root", None, "env")
    app.add_config_value("svdoc_source_url", None, "env")
    app.add_domain(SVDomain)
    app.connect("builder-inited", load_sources)
    app.connect("builder-inited", add_static_path)
    app.add_css_file("svdoc.css")
    return {"version": __version__, "parallel_read_safe": True,
            "parallel_write_safe": True, "env_version": 1}
