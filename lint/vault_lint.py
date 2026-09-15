#!/usr/bin/env python3
"""Vault lint v1 for the food planner vault.

Run from the repository root:

    python3 lint/vault_lint.py

Exit code 0 when the vault is clean, 1 with one line per violation.
No dependencies beyond the Python 3 standard library.

Checks (v1):
- every node under nodes/ has flat YAML frontmatter with core types only
- every node has `type` and `name`; `name` equals the file base name;
  base names are unique across the vault
- the Goals node follows its schema; bounds use the rounding rule
- ROUTER.md is under 500 tokens
- state.md has its fields; Open items holds no unreviewed Food lines
- index.md has one section per node type and no line without a node
- every routine file has the five sections
"""
from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

NODE_TYPES = ("food", "meal", "day", "goals", "pantry")
INDEX_SECTIONS = ("Food", "Meal", "Day", "Goals", "Pantry")
ROUTINE_SECTIONS = ("When", "Read", "Steps", "Write", "Reply")
ROUTER_TOKEN_LIMIT = 500
MACROS = ("kcal", "protein_g", "fat_g", "carbs_g")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s+(.*))?$")
INDEX_LINK_LINE_RE = re.compile(r"^- \[\[([^\]]+)\]\](?: \| .*)?$")
INDEX_DAY_LINE_RE = re.compile(r"^- (\d{4}-\d{2}) \| (nodes/day/\d{4}-\d{2}/)$")


# --------------------------------------------------------------------------
# Rules stated once and applied everywhere
# --------------------------------------------------------------------------

def round_bound(value: float) -> int:
    """Rounding rule for Goals bounds: nearest whole number, a half rounds up.

    The rule is stated for the agent in routines/goals.md step 4. This is the
    lint's application of it.
    """
    return int(math.floor(value + 0.5))


def estimate_tokens(text: str) -> int:
    """Token estimate used for the Router limit: one token per four characters."""
    return math.ceil(len(text) / 4)


# --------------------------------------------------------------------------
# Frontmatter
# --------------------------------------------------------------------------

class FrontmatterError(ValueError):
    pass


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse flat YAML frontmatter with core Obsidian types only.

    Accepts `key: scalar` and `key:` followed by `  - item` lines. Rejects
    nested mappings, flow collections and anything else. Returns the mapping
    (values as raw strings, lists as lists of raw strings) and the body.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("no frontmatter (file must start with ---)")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise FrontmatterError("frontmatter has no closing ---")
    data: dict = {}
    current_list: str | None = None
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")):
            stripped = raw.strip()
            if current_list is not None and stripped.startswith("- "):
                data[current_list].append(_scalar(stripped[2:]))
                continue
            raise FrontmatterError(f"frontmatter is not flat near {raw.strip()!r}")
        match = KEY_RE.match(raw)
        if not match:
            raise FrontmatterError(f"frontmatter line is not `key: value`: {raw!r}")
        key, value = match.group(1), match.group(2)
        if key in data:
            raise FrontmatterError(f"duplicate frontmatter key {key!r}")
        if value is None or value == "":
            data[key] = []
            current_list = key
            continue
        current_list = None
        if value.startswith(("{", "[")):
            raise FrontmatterError(f"frontmatter is not flat: {key!r} uses a flow collection")
        data[key] = _scalar(value)
    body = "\n".join(lines[end + 1:])
    return data, body


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def is_number(value) -> bool:
    return isinstance(value, str) and bool(NUMBER_RE.match(value))


def is_date(value) -> bool:
    return isinstance(value, str) and bool(DATE_RE.match(value))


# --------------------------------------------------------------------------
# Vault model
# --------------------------------------------------------------------------

@dataclass
class Node:
    rel: str
    base_name: str
    data: dict
    body: str

    @property
    def type(self):
        return self.data.get("type")


@dataclass
class Vault:
    root: Path
    nodes: list[Node] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def fail(self, rel: str, message: str) -> None:
        self.errors.append(f"{rel}: {message}")

    def node_by_name(self, name: str) -> Node | None:
        for node in self.nodes:
            if node.base_name == name:
                return node
        return None


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def load_nodes(vault: Vault) -> None:
    nodes_dir = vault.root / "nodes"
    if not nodes_dir.is_dir():
        vault.fail("nodes/", "folder is missing")
        return
    for path in sorted(nodes_dir.rglob("*.md")):
        rel = path.relative_to(vault.root).as_posix()
        try:
            data, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        except FrontmatterError as exc:
            vault.fail(rel, str(exc))
            continue
        vault.nodes.append(Node(rel, path.stem, data, body))


def check_common_conventions(vault: Vault) -> None:
    seen: dict[str, str] = {}
    for node in vault.nodes:
        if "type" not in node.data:
            vault.fail(node.rel, "missing `type`")
        elif node.type not in NODE_TYPES:
            vault.fail(node.rel, f"`type` {node.type!r} is not one of {', '.join(NODE_TYPES)}")
        if "name" not in node.data:
            vault.fail(node.rel, "missing `name`")
        elif node.data["name"] != node.base_name:
            vault.fail(node.rel, f"`name` {node.data['name']!r} differs from file base name {node.base_name!r}")
        if node.base_name in seen:
            vault.fail(node.rel, f"base name {node.base_name!r} is not unique (also {seen[node.base_name]})")
        else:
            seen[node.base_name] = node.rel


def check_goals(vault: Vault) -> None:
    goals = [n for n in vault.nodes if n.type == "goals"]
    if len(goals) > 1:
        for node in goals[1:]:
            vault.fail(node.rel, "more than one Goals node")
    for node in goals:
        data = node.data
        if node.rel != "nodes/goals/Goals.md":
            vault.fail(node.rel, "Goals node must be nodes/goals/Goals.md")
        for key in MACROS + ("tolerance_pct",):
            if key not in data:
                vault.fail(node.rel, f"missing `{key}`")
            elif not is_number(data[key]):
                vault.fail(node.rel, f"`{key}` must be a number, got {data[key]!r}")
        if "since" not in data:
            vault.fail(node.rel, "missing `since`")
        elif not is_date(data["since"]):
            vault.fail(node.rel, f"`since` must be a date YYYY-MM-DD, got {data['since']!r}")
        if not is_number(data.get("tolerance_pct", "")):
            continue
        tolerance = float(data["tolerance_pct"]) / 100
        for macro in MACROS:
            if not is_number(data.get(macro, "")):
                continue
            target = float(data[macro])
            expected = {
                f"{macro}_min": round_bound(target * (1 - tolerance)),
                f"{macro}_max": round_bound(target * (1 + tolerance)),
            }
            for key, want in expected.items():
                if key not in data:
                    vault.fail(node.rel, f"missing `{key}`")
                elif not is_number(data[key]) or float(data[key]) != want:
                    vault.fail(node.rel, f"`{key}` is {data[key]!r}, expected {want} (rounding rule: nearest whole, half up)")
        allowed = set(MACROS) | {"type", "name", "tolerance_pct", "since"} | {f"{m}_{b}" for m in MACROS for b in ("min", "max")}
        for key in data:
            if key not in allowed:
                vault.fail(node.rel, f"unexpected property `{key}` on Goals")


def check_router(vault: Vault) -> None:
    path = vault.root / "ROUTER.md"
    if not path.is_file():
        vault.fail("ROUTER.md", "file is missing")
        return
    tokens = estimate_tokens(path.read_text(encoding="utf-8"))
    if tokens >= ROUTER_TOKEN_LIMIT:
        vault.fail("ROUTER.md", f"about {tokens} tokens, limit is under {ROUTER_TOKEN_LIMIT} (estimate: characters / 4)")


def check_state(vault: Vault) -> None:
    path = vault.root / "state.md"
    if not path.is_file():
        vault.fail("state.md", "file is missing")
        return
    try:
        data, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    except FrontmatterError as exc:
        vault.fail("state.md", str(exc))
        return
    if data.get("type") != "state":
        vault.fail("state.md", "`type` must be `state`")
    if "open_day" not in data:
        vault.fail("state.md", "missing `open_day`")
    if "updated" not in data:
        vault.fail("state.md", "missing `updated`")
    elif not is_date(data["updated"]):
        vault.fail("state.md", f"`updated` must be a date YYYY-MM-DD, got {data['updated']!r}")

    open_days = [n for n in vault.nodes if n.type == "day" and n.data.get("status") == "open"]
    open_day = data.get("open_day")
    if isinstance(open_day, list):
        open_day = ""
    if open_day:
        match = WIKILINK_RE.fullmatch(open_day)
        target = vault.node_by_name(match.group(1)) if match else None
        if not match:
            vault.fail("state.md", f"`open_day` must be a quoted wikilink or empty, got {open_day!r}")
        elif target is None or target.type != "day":
            vault.fail("state.md", f"`open_day` points to {open_day!r}, which is not an existing Day node")
        elif target.data.get("status") != "open":
            vault.fail("state.md", f"`open_day` points to {open_day!r}, whose status is not open")
    elif open_days:
        vault.fail("state.md", f"`open_day` is empty but {open_days[0].rel} has status open")

    sections = _sections(body)
    if "Open items" not in sections:
        vault.fail("state.md", "missing `## Open items` section")
        return
    extra = [s for s in sections if s != "Open items"]
    if extra:
        vault.fail("state.md", f"unexpected section(s) {extra}; only `## Open items` is allowed")
    for line in sections["Open items"]:
        if re.search(r"\breviewed\b|\bunreviewed\b", line, re.IGNORECASE):
            vault.fail("state.md", f"Open items must not hold unreviewed Food lines: {line.strip()!r}")
            continue
        for name in WIKILINK_RE.findall(line):
            target = vault.node_by_name(name)
            if target is not None and target.type == "food":
                vault.fail("state.md", f"Open items links to a Food ({name}); Foods are never open items")


def check_index(vault: Vault) -> None:
    path = vault.root / "index.md"
    if not path.is_file():
        vault.fail("index.md", "file is missing")
        return
    text = path.read_text(encoding="utf-8")
    sections = _sections(text)
    for name in INDEX_SECTIONS:
        if name not in sections:
            vault.fail("index.md", f"missing `## {name}` section")
    extra = [s for s in sections if s not in INDEX_SECTIONS]
    if extra:
        vault.fail("index.md", f"unexpected section(s) {extra}")

    indexed: set[str] = set()
    for section, lines in sections.items():
        if section not in INDEX_SECTIONS:
            continue
        for line in lines:
            if not line.strip():
                continue
            if section == "Day":
                match = INDEX_DAY_LINE_RE.match(line)
                if not match:
                    vault.fail("index.md", f"Day line must be `- YYYY-MM | nodes/day/YYYY-MM/`: {line!r}")
                    continue
                month, folder = match.groups()
                if folder != f"nodes/day/{month}/":
                    vault.fail("index.md", f"Day line {month} points to {folder}")
                elif not (vault.root / folder).is_dir():
                    vault.fail("index.md", f"Day line {month} points to a folder that does not exist: {folder}")
                continue
            match = INDEX_LINK_LINE_RE.match(line)
            if not match:
                vault.fail("index.md", f"line in `## {section}` is not `- [[Name]] | ...`: {line!r}")
                continue
            name = match.group(1)
            node = vault.node_by_name(name)
            if node is None:
                vault.fail("index.md", f"line points to [[{name}]] but no node has that base name")
                continue
            if node.type != section.lower():
                vault.fail("index.md", f"[[{name}]] is a {node.type} node but sits under `## {section}`")
            if section in ("Goals", "Pantry") and " | " in line:
                vault.fail("index.md", f"{section} line must be the link only: {line!r}")
            indexed.add(name)

    for node in vault.nodes:
        if node.type in ("food", "meal", "goals", "pantry") and node.base_name not in indexed:
            vault.fail("index.md", f"no line for [[{node.base_name}]] ({node.rel})")


def check_routines(vault: Vault) -> None:
    routines = vault.root / "routines"
    if not routines.is_dir():
        return
    for path in sorted(routines.glob("*.md")):
        rel = path.relative_to(vault.root).as_posix()
        sections = _sections(path.read_text(encoding="utf-8"))
        for name in ROUTINE_SECTIONS:
            if name not in sections:
                vault.fail(rel, f"missing `## {name}` section")


def _sections(text: str) -> dict[str, list[str]]:
    """Split markdown into `## Heading` -> lines. Lines before the first heading are dropped."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.split("\n"):
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return sections


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

def lint_vault(root: Path) -> list[str]:
    vault = Vault(Path(root))
    load_nodes(vault)
    check_common_conventions(vault)
    check_goals(vault)
    check_router(vault)
    check_state(vault)
    check_index(vault)
    check_routines(vault)
    return vault.errors


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    errors = lint_vault(root)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        print(f"vault lint: {len(errors)} violation(s)")
        return 1
    print("vault lint: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
