"""``sphinx-svdoc`` command: write .rst or .md pages without running Sphinx."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__, markdown, rst
from .parser import collect_files, parse_file


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="sphinx-svdoc",
        description="Generate module documentation from SystemVerilog source. "
                    "For Sphinx projects use the sphinx_svdoc extension instead.")
    ap.add_argument("sources", nargs="+", help="SV files, directories or glob patterns")
    ap.add_argument("-o", "--out", type=Path, default=Path("svdoc-out"),
                    help="output directory (default: %(default)s)")
    ap.add_argument("-f", "--format", choices=("rst", "md"), default="rst")
    ap.add_argument("-r", "--recursive", action="store_true",
                    help="search directories recursively")
    ap.add_argument("-t", "--title", default="Module reference", help="index page title")
    ap.add_argument("--locals", action="store_true",
                    help="also document localparams and typedefs")
    ap.add_argument("--instances", action="store_true",
                    help="also list submodule instances")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)

    warn = lambda msg: print(f"warning: {msg}", file=sys.stderr)
    files = collect_files(args.sources, args.recursive)
    mods = [m for f in files for m in parse_file(f, warn)]
    if not mods:
        sys.exit("sphinx-svdoc: no modules found")

    args.out.mkdir(parents=True, exist_ok=True)
    known = {m.name for m in mods}
    for m in mods:
        rel = os.path.relpath(Path(m.file).resolve(), args.out.resolve()).replace(os.sep, "/")
        if args.format == "rst":
            text = "\n".join(rst.render_module(m, known=known, domain=False, source=rel,
                                               include_locals=args.locals,
                                               include_instances=args.instances,
                                               doc_dir=str(args.out.resolve())))
        else:
            text = markdown.render_module(m, rel, known, include_locals=args.locals,
                                          include_instances=args.instances)
        (args.out / f"{m.name}.{args.format}").write_text(text + "\n")
    if args.format == "rst":
        index = "\n".join(rst.render_index(mods, args.title))
    else:
        index = markdown.render_index(mods, args.title)
    (args.out / f"index.{args.format}").write_text(index)
    print(f"sphinx-svdoc: wrote {len(mods)} module page(s) + index.{args.format} to {args.out}/")


if __name__ == "__main__":
    main()
