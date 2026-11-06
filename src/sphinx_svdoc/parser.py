"""SystemVerilog source -> :class:`sphinx_svdoc.model.Module` using pyslang.

Only the syntax tree is used (no elaboration), so a file can be documented
on its own even when includes, packages or submodules are missing.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Callable

from pyslang import parsing as P
from pyslang import syntax as S

from .model import Instance, Item, Module
from .repeat import collapse_repeats

TK = P.TriviaKind
COMMENT_KINDS = (TK.LineComment, TK.BlockComment)
BANNER_RE = re.compile(r"[-=*#~_/+]{3,}")


def iter_tokens(node):
    """Yield every token beneath *node* in source order."""
    if isinstance(node, P.Token):
        yield node
        return
    for child in node:
        if child is None:
            continue
        yield from iter_tokens(child)


def node_text(node) -> str:
    """Source text of *node* with comments dropped and whitespace collapsed."""
    out = []
    for i, tok in enumerate(iter_tokens(node)):
        if tok.isMissing:
            continue
        if i and any(t.kind not in COMMENT_KINDS for t in tok.trivia):
            out.append(" ")
        out.append(tok.rawText)
    text = "".join(out).strip()
    return re.sub(r"\s+", " ", text)



def clean_comment(raw: str, keep_indent: bool = False) -> str:
    """Strip comment markers from one comment trivia.

    Decorative banner lines (``// -----``) become empty strings.  With
    *keep_indent*, indentation after the marker is preserved (the caller
    dedents the whole block) so that reStructuredText structure survives.
    """
    if raw.startswith("//"):
        body = re.sub(r"^//[/!]?<?", "", raw).rstrip()
        if BANNER_RE.fullmatch(body.strip()):
            return ""
        return body if keep_indent else body.strip()
    body = re.sub(r"^/\*[*!]?<?", "", raw)
    body = re.sub(r"\*/$", "", body)
    lines = body.splitlines()
    if all(re.match(r"^\s*\*", ln) for ln in lines[1:] if ln.strip()):
        lines = [lines[0]] + [re.sub(r"^\s*\* ?", "", ln) for ln in lines[1:]]
    lines = ["" if BANNER_RE.fullmatch(l.strip()) else l.rstrip() for l in lines]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    text = textwrap.dedent("\n".join(lines))
    return text if keep_indent else " ".join(text.split())

def is_doc_comment(raw: str) -> bool:
    return raw.startswith(("///", "//!", "/**", "/*!"))


def comment_blocks(trivia, skip_first_line=False):
    """Split leading trivia into blocks of consecutive comments.

    Returns ``(blocks, gap_after_last)`` where each block is a list of raw
    comment strings and ``gap_after_last`` tells whether a blank line
    separates the final block from the token.
    If *skip_first_line*, anything before the first newline (a trailing
    comment belonging to the previous item) is ignored.
    """
    blocks, cur, eols = [], [], 0
    seen_eol = not skip_first_line
    for tr in trivia:
        k = tr.kind
        if k == TK.EndOfLine:
            seen_eol = True
            eols += 1
            if eols >= 2 and cur:
                blocks.append((cur, True))
                cur = []
        elif k in COMMENT_KINDS and seen_eol:
            if eols >= 2 and cur:
                blocks.append((cur, True))
                cur = []
            cur.append(tr.getRawText())
            eols = 0
            if k == TK.BlockComment and "\n" in tr.getRawText():
                eols = 0
    if cur:
        blocks.append((cur, eols >= 2))
    return blocks


def trailing_comment(tokens, idx) -> str:
    """Comment on the same line after token ``tokens[idx]``."""
    for tok in tokens[idx + 1:]:
        for tr in tok.trivia:
            if tr.kind == TK.EndOfLine:
                return ""
            if tr.kind in COMMENT_KINDS:
                return clean_comment(tr.getRawText())
        if tok.kind not in (P.TokenKind.Comma, P.TokenKind.Semicolon):
            return ""
    return ""

# --------------------------------------------------------------------------
# Header comment: summary + reStructuredText body + :param:/:port: fields
# --------------------------------------------------------------------------
FIELD_RE = re.compile(r"^:(param|parameter|port)\s+(\w+)\s*:\s*(.*)$")


def parse_header(text: str, mod: Module) -> dict[tuple[str, str], str]:
    """Fill ``mod.summary`` / ``mod.body``; return the :param:/:port: fields.

    Fields may continue on following lines that are indented.
    """
    body, fields = [], {}
    cur = None
    for line in text.splitlines():
        m = FIELD_RE.match(line)
        if m:
            kind = "port" if m.group(1) == "port" else "param"
            cur = (kind, m.group(2))
            fields[cur] = m.group(3).strip()
            continue
        if cur is not None and line[:1].isspace() and line.strip():
            fields[cur] += " " + line.strip()
            continue
        cur = None
        body.append(line)
    text = "\n".join(body).strip("\n")
    lines = text.splitlines()
    # A first line that only repeats the module name is noise
    if lines and lines[0].strip() == mod.name:
        text = "\n".join(lines[1:]).strip("\n")
    paras = re.split(r"\n\s*\n", text, maxsplit=1)
    first = paras[0].strip()
    if first and not first.startswith((":", "..")):
        mod.summary = " ".join(first.split())
        text = paras[1] if len(paras) > 1 else ""
    mod.body = textwrap.dedent(text).strip("\n")
    return fields


def apply_field_overrides(mod: Module, fields: dict[tuple[str, str], str]):
    targets = {"param": {p.name: p for p in mod.params + mod.locals},
               "port": {p.name: p for p in mod.ports}}
    for (kind, name), text in fields.items():
        item = targets[kind].get(name)
        if item is not None:
            item.doc = text
        else:
            # Unknown name: keep it visible rather than silently dropping it
            mod.body += f"\n\n:{kind} {name}: {text}"


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------
def split_block(raw_block):
    """Split a comment run into (plain comments, trailing ``///`` doc comments)."""
    i = len(raw_block)
    while i and is_doc_comment(raw_block[i - 1]):
        i -= 1
    return raw_block[:i], raw_block[i:]


def join_inline(raws) -> str:
    return " ".join(filter(None, (clean_comment(r) for r in raws)))


NODOC_RE = re.compile(r":nodoc:(\s.*)?", re.IGNORECASE | re.DOTALL)


def is_nodoc(text: str) -> bool:
    """``:nodoc:``, optionally followed by a note for source readers."""
    return bool(NODOC_RE.fullmatch(text.strip()))


def take_nodoc(blocks):
    """Remove ``// :nodoc:`` comments from the block attached to an item.

    Returns ``(hidden, blocks)``.  Only the block directly above the item
    (no blank line in between) counts.
    """
    if not blocks or blocks[-1][1]:
        return False, blocks
    raws = blocks[-1][0]
    keep = [r for r in raws if not is_nodoc(clean_comment(r))]
    if len(keep) == len(raws):
        return False, blocks
    return True, blocks[:-1] + ([(keep, False)] if keep else [])


MARKER_RE = re.compile(r"^:(category|bundle|endcategory|endbundle):(?:\s+(.*))?$",
                       re.IGNORECASE)


def _marker(raw: str):
    """``(kind, title, rest)`` if *raw* starts with a structure marker.

    *kind* is ``category``, ``bundle``, ``endcategory`` or ``endbundle``;
    *rest* is the remainder of a multi-line ``/* */`` comment.
    """
    lines = clean_comment(raw, keep_indent=True).strip("\n").splitlines()
    m = MARKER_RE.match(lines[0].strip()) if lines else None
    if not m:
        return None
    return m.group(1).lower(), (m.group(2) or "").strip(), "\n".join(lines[1:])


class Scope:
    """Current category / bundle while walking a list of declarations."""

    def __init__(self, mod: Module):
        self.mod = mod
        self.category = ""
        self.bundle = ""

    def apply(self, kind: str, title: str, desc: str):
        if kind == "category":
            self.category, self.bundle = title, ""
            if desc:
                self.mod.category_docs[title] = desc
        elif kind == "bundle":
            self.bundle = title
            if desc:
                self.mod.bundle_docs[title] = desc
        elif kind == "endbundle":
            self.bundle = ""
        elif kind == "endcategory":
            self.category = self.bundle = ""


def leading_comments(blocks, scope: Scope) -> str:
    """Apply structure markers in front of an item; return the item's doc.

    ``// :category: Title`` / ``// :bundle: Title`` start a category or a
    bundle; comment lines after the marker (up to the next marker) are its
    description (reStructuredText).  ``// :endbundle:`` / ``// :endcategory:``
    close them.  The item's own description is a run of ``///`` comments
    directly above it.  Plain ``//`` comments are ignored.
    """
    doc = ""
    for bi, (raws, gap) in enumerate(blocks):
        attached = bi == len(blocks) - 1 and not gap
        marks = [(i, mk) for i, r in enumerate(raws) if (mk := _marker(r))]
        if not marks:
            if attached:
                doc = join_inline(split_block(raws)[1])
            continue
        for k, (i, (kind, title, head)) in enumerate(marks):
            end = marks[k + 1][0] if k + 1 < len(marks) else len(raws)
            rest = raws[i + 1:end]
            if attached and k == len(marks) - 1 and not is_doc_comment(raws[i]):
                rest, item_doc = split_block(rest)   # trailing /// run -> the item
                doc = join_inline(item_doc)
            parts = ([textwrap.dedent(head)] if head.strip() else []) + \
                [clean_comment(r, keep_indent=True) for r in rest]
            scope.apply(kind, title, textwrap.dedent("\n".join(parts)).strip("\n"))
    return doc


def list_items(nodes, tokens, tok_index, make_items, mod: Module):
    """Walk a port / parameter list collecting items, categories and bundles."""
    items, scope = [], Scope(mod)
    for child in nodes:
        if isinstance(child, P.Token) or child is None:
            continue
        first = child.getFirstToken()
        blocks = comment_blocks(first.trivia, skip_first_line=True)
        hidden, blocks = take_nodoc(blocks)
        doc = leading_comments(blocks, scope)
        new = make_items(child)
        trail = trailing_comment(tokens, tok_index[id_key(child.getLastToken())])
        if is_nodoc(trail):
            hidden, trail = True, ""
        for it in new:
            it.hidden = hidden
            it.category, it.bundle = scope.category, scope.bundle
            it.doc = doc or trail
        items.extend(new)
    return items


def id_key(tok):
    return (tok.location.offset, tok.kind)


def param_items(decl):
    """ParameterDeclaration / TypeParameterDeclaration -> Items."""
    kw = decl.keyword.valueText if decl.keyword and not decl.keyword.isMissing else "parameter"
    out = []
    if decl.kind == S.SyntaxKind.TypeParameterDeclaration:
        for d in decl.declarators:
            if isinstance(d, P.Token):
                continue
            out.append(Item(d.name.valueText, kw, "type",
                            node_text(d.assignment.type) if d.assignment else ""))
        return out
    typ = node_text(decl.type) if decl.type else ""
    for d in decl.declarators:
        if isinstance(d, P.Token):
            continue
        dims = "".join(node_text(x) for x in d.dimensions)
        default = node_text(d.initializer.expr) if d.initializer else ""
        out.append(Item(d.name.valueText, kw, (typ + " " + dims).strip(), default))
    return out


def port_items(port):
    k = port.kind
    if k == S.SyntaxKind.ImplicitAnsiPort:
        h = port.header
        direction = ""
        typ = ""
        if h.kind in (S.SyntaxKind.VariablePortHeader, S.SyntaxKind.NetPortHeader):
            direction = h.direction.valueText if h.direction else ""
            parts = []
            if h.kind == S.SyntaxKind.NetPortHeader and h.netType:
                parts.append(h.netType.valueText)
            elif h.kind == S.SyntaxKind.VariablePortHeader and getattr(h, "varKeyword", None):
                if h.varKeyword.valueText:
                    parts.append(h.varKeyword.valueText)
            parts.append(node_text(h.dataType))
            typ = " ".join(p for p in parts if p)
        elif h.kind == S.SyntaxKind.InterfacePortHeader:
            direction = "interface"
            typ = node_text(h)
        else:
            typ = node_text(h)
        d = port.declarator
        dims = "".join(node_text(x) for x in d.dimensions)
        if dims:
            typ += f" (unpacked {dims})"
        return [Item(d.name.valueText, direction or "(inherit)", typ)]
    # Non-ANSI / explicit ports: just the name
    return [Item(node_text(port), "", "")]


def body_items(members, tokens, tok_index, mod: Module):
    """parameter / localparam / typedef members of the module body.

    Category markers work as in port lists; they are honoured in front of
    any module item, so a ``// :category:`` above other code still applies
    to the declarations that follow it.
    """
    out, scope = [], Scope(mod)
    for member in members:
        if member is None or isinstance(member, P.Token):
            continue
        blocks = comment_blocks(member.getFirstToken().trivia, skip_first_line=True)
        hidden, blocks = take_nodoc(blocks)
        doc = leading_comments(blocks, scope)
        k = member.kind
        if k == S.SyntaxKind.ParameterDeclarationStatement:
            items = param_items(member.parameter)
        elif k == S.SyntaxKind.TypedefDeclaration:
            typ = member.type
            typ_txt = node_text(typ)
            if typ.kind == S.SyntaxKind.EnumType:
                base = node_text(typ.baseType) if typ.baseType else "int"
                names = [m.name.valueText for m in typ.members if not isinstance(m, P.Token)]
                typ_txt = f"enum {base} {{{', '.join(names)}}}"
            elif len(typ_txt) > 80:
                typ_txt = typ_txt[:77] + "..."
            items = [Item(member.name.valueText, "typedef", typ_txt)]
        else:
            continue
        trail = trailing_comment(tokens, tok_index[id_key(member.getLastToken())])
        if is_nodoc(trail):
            hidden, trail = True, ""
        for it in items:
            it.hidden = hidden
            it.doc = doc or trail
            it.category, it.bundle = scope.category, scope.bundle
        out.extend(items)
    return out


def find_instances(node, out):
    for child in node:
        if child is None or isinstance(child, P.Token):
            continue
        if child.kind == S.SyntaxKind.HierarchyInstantiation:
            mod_name = child.type.valueText
            for inst in child.instances:
                if isinstance(inst, P.Token):
                    continue
                name = inst.decl.name.valueText if inst.decl else "(unnamed)"
                out.append(Instance(mod_name, name))
        elif child.kind in NESTED_DECLS:
            continue  # nested modules are documented separately
        else:
            find_instances(child, out)


NESTED_DECLS = (S.SyntaxKind.ModuleDeclaration, S.SyntaxKind.InterfaceDeclaration,
                S.SyntaxKind.ProgramDeclaration)


def extract_module(decl, tree, path: Path) -> Module:
    hdr = decl.header
    mod = Module(hdr.name.valueText, path,
                 tree.sourceManager.getLineNumber(hdr.name.location),
                 keyword=hdr.moduleKeyword.valueText)
    tokens = list(iter_tokens(decl))
    tok_index = {id_key(t): i for i, t in enumerate(tokens)}

    fields = {}
    blocks = comment_blocks(decl.getFirstToken().trivia)
    if blocks:
        raw_block, _gap = blocks[-1]
        parts = [clean_comment(r, keep_indent=True) for r in raw_block]
        fields = parse_header(textwrap.dedent("\n".join(parts)), mod)

    if hdr.parameters:
        decls = [d for d in hdr.parameters.declarations if not isinstance(d, P.Token)]
        mod.params = list_items(decls, tokens, tok_index, param_items, mod)
    if hdr.ports and hdr.ports.kind in (S.SyntaxKind.AnsiPortList,
                                        S.SyntaxKind.NonAnsiPortList):
        ports = [p for p in hdr.ports.ports if not isinstance(p, P.Token)]
        mod.ports = list_items(ports, tokens, tok_index, port_items, mod)
        for prev, cur in zip(mod.ports, mod.ports[1:]):   # `output logic a, b`
            if cur.kind == "(inherit)":
                cur.kind, cur.type = prev.kind, cur.type or prev.type

    body = body_items(decl.members, tokens, tok_index, mod)
    if hdr.parameters is None:
        # No #( ) list: body `parameter`s are the module's real parameters
        mod.params = [i for i in body if i.kind == "parameter"]
        mod.locals = [i for i in body if i.kind != "parameter"]
    else:
        # With a #( ) list, body `parameter`s act as localparams (IEEE 1800 6.20.1)
        for i in body:
            if i.kind == "parameter":
                i.kind = "localparam"
        mod.locals = body
    find_instances(decl.members, mod.instances)
    apply_field_overrides(mod, fields)
    collapse_repeats(mod)
    return mod


def parse_file(path: Path, warn: Callable[[str], None] | None = None) -> list[Module]:
    """Return every module / interface declared in *path*."""
    path = Path(path)
    tree = S.SyntaxTree.fromFile(str(path))
    errs = [d for d in tree.diagnostics if d.isError()]
    if errs and warn:
        warn(f"{path}: {len(errs)} parse error(s); documentation may be partial")
    mods: list[Module] = []

    def walk(node):
        for child in node:
            if child is None or isinstance(child, P.Token):
                continue
            if child.kind in (S.SyntaxKind.ModuleDeclaration,
                              S.SyntaxKind.InterfaceDeclaration):
                mods.append(extract_module(child, tree, path))
                walk(child.members)
            elif child.kind == S.SyntaxKind.CompilationUnit:
                walk(child)

    walk(tree.root)
    return mods


def collect_files(sources, recursive=False) -> list[Path]:
    """Expand files / directories / glob patterns into a list of SV files."""
    out: list[Path] = []
    for src in map(str, sources):
        if any(c in src for c in "*?["):
            out += sorted(Path(p) for p in __import__("glob").glob(src, recursive=True))
            continue
        p = Path(src)
        if p.is_dir():
            for pat in ("*.sv", "*.svh", "*.v"):
                out += sorted(p.rglob(pat) if recursive else p.glob(pat))
        else:
            out.append(p)
    seen, uniq = set(), []
    for p in out:
        if p.resolve() not in seen:
            seen.add(p.resolve())
            uniq.append(p)
    return uniq
