"""Data model shared by the parser and the renderers."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Item:
    """A parameter, port, localparam or typedef."""
    name: str
    kind: str = ""        # port direction, or 'parameter' / 'localparam' / 'typedef'
    type: str = ""
    default: str = ""
    doc: str = ""         # description (plain text from an inline comment)
    category: str = ""    # from a `// :category: Title` marker
    bundle: str = ""      # from a `// :bundle: Title` marker (inside a category)
    hidden: bool = False  # marked ':nodoc:' -> parsed but not rendered
    indices: list[str] = field(default_factory=list)  # name has '<n>': its values


@dataclass
class Instance:
    module: str           # instantiated module/interface name
    name: str             # instance name


@dataclass
class Module:
    name: str
    file: Path
    line: int
    keyword: str = "module"   # 'module' or 'interface'
    summary: str = ""         # first paragraph of the header comment
    body: str = ""            # remaining header comment, reStructuredText
    params: list[Item] = field(default_factory=list)
    ports: list[Item] = field(default_factory=list)
    locals: list[Item] = field(default_factory=list)
    instances: list[Instance] = field(default_factory=list)
    category_docs: dict[str, str] = field(default_factory=dict)  # title -> RST description
    bundle_docs: dict[str, str] = field(default_factory=dict)    # title -> RST description
    bundle_repeat: dict[str, list[str]] = field(default_factory=dict)  # title -> <n> values

    # Documented (non-hidden) views used by the renderers
    @property
    def doc_params(self) -> list[Item]:
        return [i for i in self.params if not i.hidden]

    @property
    def doc_ports(self) -> list[Item]:
        return [i for i in self.ports if not i.hidden]

    @property
    def localparams(self) -> list[Item]:
        return [i for i in self.locals if i.kind != "typedef" and not i.hidden]

    @property
    def typedefs(self) -> list[Item]:
        return [i for i in self.locals if i.kind == "typedef" and not i.hidden]
