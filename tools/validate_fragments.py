#!/usr/bin/env python3
"""
validate_fragments.py — Memory Fragment ↔ Graph.json cross-validator (M5).

Per CHRONOS_SWITCH.md §8 milestone M5, this script is the build-time
guard against silent authoring drift between Memory Fragments (live in
TypeScript) and the narrative graph (lives in Graph.json). Without it,
a renamed flag in one file and not the other would compile cleanly and
fail only when a player triggers the echo and nothing happens.

What it checks:
  1. Each `new MemoryFragment(..., "<id>", ...)` in the source tree has a
     matching `pastSceneController.begin({ fragmentId: "<id>", ...,
     unlocksFlag: "<flag>" })` Past-scene spec in the same file.
  2. Each fragment id has exactly one graph node tagged
     `"fragmentId": "<id>"`, and that node's `unlocksFlags` contains the
     `<flag>` declared by the Past-scene spec.
  3. Each `fragmentId` declared on a graph node has a corresponding
     `new MemoryFragment(...)` in code.
  4. No duplicate fragment ids in code or graph.

Usage:
  python3 tools/validate_fragments.py
    → exit 0 with a green report when all bindings resolve.
    → exit 1 with a list of authoring errors otherwise.

Optional flags:
  --src     Path to the witness-interactive-vite/src/ root.
            Defaults to <repo>/witness-interactive-vite/src.
  --graph   Path to Graph.json. Defaults to <src>/narrative/Graph.json.
  --json    Emit machine-readable JSON to stdout instead of the text
            report (useful for CI consumers).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC_ROOT = REPO_ROOT / "witness-interactive-vite" / "src"
SKIP_DIRS = {"_prototype-archive", "node_modules", ".vite", "dist"}

FRAGMENT_DECL_RE = re.compile(
    r'\bnew\s+MemoryFragment\s*\(\s*([^,]+),\s*"([^"]+)"',
    re.MULTILINE,
)
# Matches both the direct call and the beginWithBreath wrapper that spreads
# the spec. The wrapper calls pastSceneController.begin({...spec}) internally,
# so fragmentId/unlocksFlag are only visible at the beginWithBreath call site.
BEGIN_OPEN_RE = re.compile(
    r'\b(?:pastSceneController\s*\.\s*begin|beginWithBreath)\s*\(\s*\{'
)
SPEC_FRAGMENT_ID_RE = re.compile(r'\bfragmentId\s*:\s*"([^"]+)"')
SPEC_UNLOCKS_FLAG_RE = re.compile(r'\bunlocksFlag\s*:\s*"([^"]+)"')


@dataclass
class CodeFragment:
    id: str
    file: str
    line: int
    anchor_expr: str
    unlocks_flag: str | None = None
    spec_file: str | None = None
    spec_line: int | None = None


@dataclass
class GraphBinding:
    node_id: str
    fragment_id: str
    unlocks_flags: list[str]


def find_balanced_block(text: str, start: int) -> tuple[str | None, int]:
    """Walk forward from text[start] (which must be '{') and return the
    inner body of the first balanced '{...}' plus the index just past
    the closing brace. String- and comment-aware so braces inside string
    literals or `// ...` / `/* ... */` runs do not throw off the count.

    Returns (None, end_idx) on unterminated input.
    """
    if start >= len(text) or text[start] != "{":
        return (None, start)
    depth = 1
    i = start + 1
    n = len(text)
    while i < n and depth > 0:
        c = text[i]
        if c == '"' or c == "'":
            quote = c
            i += 1
            while i < n and text[i] != quote:
                i += 2 if text[i] == "\\" else 1
            i += 1
        elif c == "`":
            i += 1
            while i < n and text[i] != "`":
                i += 2 if text[i] == "\\" else 1
            i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
        elif c == "{":
            depth += 1
            i += 1
        elif c == "}":
            depth -= 1
            i += 1
        else:
            i += 1
    if depth != 0:
        return (None, i)
    return (text[start + 1 : i - 1], i)


def line_at(text: str, idx: int) -> int:
    """1-indexed line number for an offset in `text`."""
    return text.count("\n", 0, idx) + 1


def iter_typescript_files(src_root: Path):
    for path in sorted(src_root.rglob("*.ts")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def collect_code_fragments(
    src_root: Path,
) -> tuple[list[CodeFragment], list[str]]:
    """Walk *.ts under src_root, return (fragments, errors). The
    fragments list reflects every `new MemoryFragment(...)` we found,
    paired with its Past-scene spec when present. Authoring failures
    (duplicates, missing specs, orphan specs) accumulate in errors."""
    errors: list[str] = []
    fragments_by_id: dict[str, CodeFragment] = {}

    for ts in iter_typescript_files(src_root):
        text = ts.read_text(encoding="utf-8")
        rel = ts.relative_to(src_root)

        for m in FRAGMENT_DECL_RE.finditer(text):
            anchor_expr = m.group(1).strip()
            fid = m.group(2)
            line = line_at(text, m.start())
            existing = fragments_by_id.get(fid)
            if existing is not None:
                errors.append(
                    f"duplicate fragment id '{fid}': "
                    f"first at {existing.file}:{existing.line}, "
                    f"second at {rel}:{line}"
                )
                continue
            fragments_by_id[fid] = CodeFragment(
                id=fid, file=str(rel), line=line, anchor_expr=anchor_expr
            )

        for m in BEGIN_OPEN_RE.finditer(text):
            brace_idx = m.end() - 1
            body, _ = find_balanced_block(text, brace_idx)
            spec_line = line_at(text, m.start())
            if body is None:
                errors.append(
                    f"unterminated pastSceneController.begin spec at "
                    f"{rel}:{spec_line}"
                )
                continue
            fid_match = SPEC_FRAGMENT_ID_RE.search(body)
            if fid_match is None:
                # Skip the internal relay call in beginWithBreath, which
                # spreads the spec object: pastSceneController.begin({...spec}).
                # Its fragmentId is captured at the beginWithBreath call site.
                if body.lstrip().startswith("..."):
                    continue
                errors.append(
                    f"pastSceneController.begin without fragmentId at "
                    f"{rel}:{spec_line}"
                )
                continue
            spec_fid = fid_match.group(1)
            flag_match = SPEC_UNLOCKS_FLAG_RE.search(body)
            if flag_match is None:
                errors.append(
                    f"pastSceneController.begin('{spec_fid}') without "
                    f"unlocksFlag at {rel}:{spec_line}"
                )
                continue
            frag = fragments_by_id.get(spec_fid)
            if frag is None:
                errors.append(
                    f"pastSceneController.begin spec for '{spec_fid}' at "
                    f"{rel}:{spec_line} has no matching "
                    f'`new MemoryFragment(..., "{spec_fid}", ...)` under '
                    f"{src_root}"
                )
                continue
            if frag.unlocks_flag is not None:
                errors.append(
                    f"duplicate pastSceneController.begin spec for "
                    f"'{spec_fid}': first at {frag.spec_file}:{frag.spec_line}, "
                    f"second at {rel}:{spec_line}"
                )
                continue
            frag.unlocks_flag = flag_match.group(1)
            frag.spec_file = str(rel)
            frag.spec_line = spec_line

    for frag in fragments_by_id.values():
        if frag.unlocks_flag is None:
            errors.append(
                f"fragment '{frag.id}' constructed at {frag.file}:{frag.line} "
                f"has no `pastSceneController.begin({{ fragmentId: "
                f'"{frag.id}", ... }})` spec'
            )

    return list(fragments_by_id.values()), errors


def collect_graph_bindings(
    graph_path: Path,
) -> tuple[list[GraphBinding], list[str]]:
    """Read Graph.json and pull out every node carrying a `fragmentId`."""
    errors: list[str] = []
    if not graph_path.is_file():
        return ([], [f"graph file missing: {graph_path}"])
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return ([], [f"graph parse failed: {e}"])

    bindings_by_fid: dict[str, GraphBinding] = {}
    for node in data.get("nodes", []):
        fid = node.get("fragmentId")
        if fid is None:
            continue
        node_id = node.get("id", "<no id>")
        flags = list(node.get("unlocksFlags", []))
        if fid in bindings_by_fid:
            errors.append(
                f"duplicate fragmentId '{fid}' in Graph.json: "
                f"nodes '{bindings_by_fid[fid].node_id}' and '{node_id}'"
            )
            continue
        bindings_by_fid[fid] = GraphBinding(
            node_id=node_id, fragment_id=fid, unlocks_flags=flags
        )

    return list(bindings_by_fid.values()), errors


def cross_validate(
    fragments: list[CodeFragment], bindings: list[GraphBinding]
) -> list[str]:
    """Bidirectional binding check. Each fragment must reach a graph
    node by id, that node's unlocksFlags must include the fragment's
    declared flag, and every graph binding must have a code fragment."""
    errors: list[str] = []
    fragments_by_id = {f.id: f for f in fragments}
    bindings_by_fid = {b.fragment_id: b for b in bindings}

    for frag in fragments:
        if frag.unlocks_flag is None:
            continue
        binding = bindings_by_fid.get(frag.id)
        if binding is None:
            errors.append(
                f"fragment '{frag.id}' (in {frag.file}:{frag.line}) has no "
                f'graph node with `fragmentId: "{frag.id}"` — narrative '
                f"would not advance after the echo"
            )
            continue
        if frag.unlocks_flag not in binding.unlocks_flags:
            errors.append(
                f"fragment '{frag.id}' unlocks flag '{frag.unlocks_flag}' "
                f"(spec at {frag.spec_file}:{frag.spec_line}) but graph "
                f"node '{binding.node_id}' declares "
                f"unlocksFlags={binding.unlocks_flags}"
            )

    for binding in bindings:
        if binding.fragment_id not in fragments_by_id:
            errors.append(
                f"graph node '{binding.node_id}' declares fragmentId "
                f"'{binding.fragment_id}' but no `new MemoryFragment(..., "
                f'"{binding.fragment_id}", ...)` exists in code'
            )

    return errors


def emit_text_report(
    fragments: list[CodeFragment],
    bindings: list[GraphBinding],
    errors: list[str],
) -> None:
    bar = "━" * 56
    print(bar)
    print("Memory Fragment ↔ Graph.json validator (M5)")
    print(bar)
    print(f"Code fragments found: {len(fragments)}")
    for f in sorted(fragments, key=lambda x: x.id):
        flag = f.unlocks_flag or "(missing)"
        print(
            f"  • {f.id:<22} → unlocksFlag={flag:<28} "
            f"({f.file}:{f.line})"
        )
    print(f"Graph bindings found: {len(bindings)}")
    for b in sorted(bindings, key=lambda x: x.fragment_id):
        print(
            f"  • {b.fragment_id:<22} → node={b.node_id:<26} "
            f"flags={b.unlocks_flags}"
        )
    print(bar)
    if errors:
        print(f"FAIL — {len(errors)} authoring error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        print(bar)
    else:
        print("OK — all fragments are wired into the narrative graph.")
        print(bar)


def emit_json_report(
    fragments: list[CodeFragment],
    bindings: list[GraphBinding],
    errors: list[str],
) -> None:
    payload = {
        "ok": not errors,
        "fragments": [asdict(f) for f in fragments],
        "bindings": [asdict(b) for b in bindings],
        "errors": errors,
    }
    print(json.dumps(payload, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Memory Fragment ↔ Graph.json bindings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=DEFAULT_SRC_ROOT,
        help=f"Source root to scan for *.ts. Default: {DEFAULT_SRC_ROOT}",
    )
    parser.add_argument(
        "--graph",
        type=Path,
        default=None,
        help="Path to Graph.json. Default: <src>/narrative/Graph.json",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable text",
    )
    args = parser.parse_args()

    src_root = args.src.resolve()
    graph_path = (
        args.graph or (src_root / "narrative" / "Graph.json")
    ).resolve()

    if not src_root.is_dir():
        print(f"ERROR: source root not found: {src_root}", file=sys.stderr)
        return 2

    fragments, code_errors = collect_code_fragments(src_root)
    bindings, graph_errors = collect_graph_bindings(graph_path)
    cross_errors = cross_validate(fragments, bindings)
    errors = code_errors + graph_errors + cross_errors

    if args.json:
        emit_json_report(fragments, bindings, errors)
    else:
        emit_text_report(fragments, bindings, errors)

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
