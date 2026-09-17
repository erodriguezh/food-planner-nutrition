#!/usr/bin/env python3
"""Seeded-day acceptance run for the food planner vault (#28).

Run from the repository root:

    python3 acceptance/seeded_day.py            # Monday of the current week
    python3 acceptance/seeded_day.py --date 2026-09-14 --keep

The run repeats the prototype conversation (branch `prototype/seeded-day`,
wayfinder #11) against the vault as built on the current HEAD, on a throwaway
branch in its own git worktree. A scripted stand-in plays the agent: it reads
the routine files, resolves names through the alias table, converts servings to
grams, computes the macros with the same rounding rule the lint applies, and
writes the files the routines say to write, one commit per routine step named
`<routine>: <one line>`. There is no model in the loop.

The seam is the files. After every turn the script asserts what is on disk:
the Day lines and totals, the `~` on the guessed line and on the Day, the new
Food unreviewed with its Index line, the State open day, the Summary verdict
words, the commit subjects, and the fixed lines of the review reply.

The vault lint runs inside `Session.commit()`, the one commit wrapper: every
routine step commits, then the real `vault_lint.lint_vault()` reads that exact
committed tree, and a lint error stops the run before the next routine step.
Chained steps inside one turn, `create-food` and `log` in turn 3, are each
gated on their own commit. The report prints the result per commit. After
every turn the worktree must be clean. Reads per turn stay under ten files.

Read budget model: a turn is one message inside a chat session. A file the
agent opened earlier in the same session is in its context and is not read
again; a file the agent writes leaves the context, so the next turn reads it
fresh before it writes it again (Router hard rule 5). Turn 9 starts a new
session, the next morning. The report prints both numbers per turn: the files
read from disk and the files the turn used.

The Croissant fixture, its numbers and aliases, comes from the prototype
branch. The throwaway branch is deleted at the end unless `--keep` is given;
nothing is ever pushed and `main` is never touched.

Exit code 0 when every turn passes, 1 on the first failing assertion.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lint"))

from vault_lint import (  # noqa: E402
    MACROS,
    NUTRIENTS,
    SLOTS,
    SUMMARY_MACROS,
    SUMMARY_SEPARATOR,
    SUMMARY_TABLE_HEADER,
    TOTALS,
    _decimal,
    _num,
    _sections,
    entry_totals,
    lint_vault,
    parse_alias_table,
    parse_entry_line,
    parse_frontmatter,
    resolve_name,
    round_food_value,
    round_total,
)

ROUTINES = ("log", "rebalance", "close-day", "create-food", "create-meal", "pantry", "goals", "review")
COMMIT_SUBJECT_RE = re.compile(rf"^(?:{'|'.join(re.escape(r) for r in ROUTINES)}): \S[^\n]*$")
READ_BUDGET = 10
"""Reads per turn stay under ten files (spec #22 story 6)."""
BRANCH_PREFIX = "acceptance/seeded-day-"
SERVING_PARTS_RE = re.compile(r"^(\d+(?:\.\d+)?) ([A-Za-z][A-Za-z ]*) = (\d+(?:\.\d+)?) g$")
"""A serving alias split into count, unit and grams; `vault_lint.SERVING_RE` only validates the shape."""
UNITS = dict(zip(SUMMARY_MACROS, ("kcal", "P", "F", "C")))
"""The chat and Summary unit word per macro, in the column order."""


def macro_line(values: Mapping[str, object], marked: bool = False) -> str:
    """`<kcal> kcal · <P> P · <F> F · <C> C` from a mapping keyed by the Day properties, `~` before every number when marked."""
    return " · ".join(f"{'~' if marked else ''}{_num(values[key])} {UNITS[macro]}" for macro, key in zip(SUMMARY_MACROS, MACROS))


class Failed(AssertionError):
    """One failed assertion of the run, or one failed git command."""


# --------------------------------------------------------------------------
# Renderers: the shapes the routines say to write
# --------------------------------------------------------------------------

def render_frontmatter(items: Iterable[tuple[str, str | list[str]]]) -> str:
    """Flat YAML frontmatter in the vault's own style: `key: value`, lists as `  - item` lines."""
    lines = ["---"]
    for key, value in items:
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def entry_line(name: str, amount: str | int, unit: str, macros: Mapping[str, int], marked: bool = False,
               change: tuple[str, str | int] | None = None) -> str:
    """The canonical entry line of routines/log.md step 5."""
    mark = "~ " if marked else ""
    changed = f", [[{change[0]}]] = {change[1]} g" if change else ""
    return f"- {mark}[[{name}]] = {amount} {unit}{changed} — {macro_line(macros)}"


def pick_slot(word: str | None, clock: datetime.time, filled: set[str]) -> str:
    """routines/log.md step 3: the word, else the clock, else the next slot in order after a filled one."""
    if word:
        return word
    hour = clock.hour
    slot = "breakfast" if hour < 11 else "lunch" if hour < 15 else "snack" if hour < 18 else "dinner"
    index = SLOTS.index(slot)
    while slot in filled and index + 1 < len(SLOTS):
        index += 1
        slot = SLOTS[index]
    return slot


def verdict(totals: Mapping[str, Decimal], bounds: Mapping[str, tuple[Decimal, Decimal]]) -> str:
    """routines/close-day.md step 5, the fixed words."""
    off = []
    for macro in SUMMARY_MACROS:
        low, high = bounds[macro]
        if totals[macro] < low:
            off.append(f"{macro} low")
        elif totals[macro] > high:
            off.append(f"{macro} high")
    return "off target: " + ", ".join(off) if off else "on target"


def _mark(value: object, marked: bool) -> str:
    return ("~" if marked else "") + _num(value)


def render_summary(slot_sums: Mapping[str, Mapping[str, object]], totals: Mapping[str, object],
                   goals: Mapping[str, Decimal], bounds: Mapping[str, tuple[Decimal, Decimal]],
                   marked: bool, hint: str | None) -> list[str]:
    """The `## Summary` body of routines/close-day.md steps 2 to 6, as lines."""
    lines = [SUMMARY_TABLE_HEADER, SUMMARY_SEPARATOR]
    for slot in SLOTS:
        if slot in slot_sums:
            lines.append("| " + " | ".join([slot] + [_mark(slot_sums[slot][key], marked) for key in MACROS]) + " |")
    lines.append("| " + " | ".join(["TOTAL"] + [_mark(totals[key], marked) for key in MACROS]) + " |")
    lines.append("")
    goal_parts = [f"{_num(goals[m])} {UNITS[m]} ({_num(bounds[m][0])}-{_num(bounds[m][1])})" for m in SUMMARY_MACROS]
    lines.append("Goal " + ", ".join(goal_parts) + ".")
    lines.append("")
    plain = {macro: _decimal(totals[key]) for macro, key in zip(SUMMARY_MACROS, MACROS)}
    for macro in SUMMARY_MACROS:
        diff = plain[macro] - goals[macro]
        lines.append(f"- {macro} {_num(abs(diff).normalize())} {'over' if diff > 0 else 'under'}")
    lines.append("")
    lines.append(verdict(plain, bounds))
    if hint:
        lines.append("")
        lines.append(f"Hint: {hint}")
    return lines


@dataclass
class DaySummary:
    """What the review needs from one Day file."""
    date: str
    status: str
    estimated: bool
    totals: Mapping[str, Decimal]
    verdict: str | None


def review_reply(days: Iterable[DaySummary], goals: Mapping[str, Decimal], today: datetime.date) -> list[str]:
    """routines/review.md Reply: the fixed lines of "how was my week" (this week, Monday to today)."""
    monday = today - datetime.timedelta(days=today.weekday())
    eligible = [(monday + datetime.timedelta(days=i)).isoformat() for i in range((today - monday).days + 1)]
    by_date = {day.date: day for day in days if day.date in eligible}
    counted = [by_date[d] for d in eligible if d in by_date and by_date[d].status in ("closed", "auto-closed")]
    open_days = [by_date[d] for d in eligible if d in by_date and by_date[d].status == "open"]
    missing = [d for d in eligible if d not in by_date]
    auto = sum(1 for day in counted if day.status == "auto-closed")
    lines = [f"Days: {len(counted)} of {len(eligible)} closed, {auto} auto-closed, missing {', '.join(missing) or 'none'}"]
    labels = dict(zip(TOTALS, tuple(UNITS.values()) + ("fiber", "sugar", "salt")))
    if counted:
        marked = any(day.estimated for day in counted)
        parts = []
        for key in TOTALS:
            exact = sum((day.totals[key] for day in counted), Decimal(0)) / len(counted)
            value = round_food_value(exact) if key in NUTRIENTS else round_total(exact)
            parts.append(f"{'~' if marked else ''}{value} {labels[key]}")
        lines.append("Average: " + " · ".join(parts))
    else:
        lines.append("Average: n/a")
    lines.append("Target: " + " · ".join(f"{_num(goals[m])} {labels[k]}" for m, k in zip(SUMMARY_MACROS, MACROS)))
    on_target = sum(1 for day in counted if day.verdict == "on target")
    lines.append(f"On target: {on_target} of {len(counted)}")
    misses: dict[str, int] = {}
    for day in counted:
        if day.verdict and day.verdict.startswith("off target: "):
            for item in day.verdict[len("off target: "):].split(", "):
                misses[item] = misses.get(item, 0) + 1
    if misses:
        top = max(misses.values())
        order = [f"{macro} {direction}" for macro in SUMMARY_MACROS for direction in ("low", "high")]
        tied = [item for item in order if misses.get(item) == top]
        lines.append("Most common miss: " + "; ".join(f"{item}, {top} days" for item in tied))
    else:
        lines.append("Most common miss: none")
    for day in open_days:
        lines.append(f"{day.date} is open and not counted.")
    return lines


# --------------------------------------------------------------------------
# Git and the session
# --------------------------------------------------------------------------

def git(root: Path, *args: str) -> str:
    """One git command in `root`.

    Background maintenance is off, so a run leaves no process behind that
    writes into a folder being removed. The `GIT_*` variables a git hook sets
    are dropped, so a run started from the pre-commit hook still acts on
    `root` and not on the repository that runs the hook. A failure raises with
    git's own message.
    """
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(["git", "-c", "gc.auto=0", "-C", str(root), *args], capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise Failed(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


@dataclass(frozen=True)
class CommitRecord:
    """One routine-step commit whose committed tree the lint accepted.

    `Session.commit()` records a commit only after the lint of that commit's
    tree comes back clean, so the record itself is the green result. There is
    no field for the result: a field could only ever hold one value.
    """
    subject: str
    sha: str


class Session:
    """The agent's file access inside one chat session, with the read budget.

    `reads` are the files opened from disk in the current turn; `used` are the
    files the turn worked with, cached ones included. A written file leaves the
    context, so the rule "read fresh before you write" costs a read next time.
    `commits` are the commits of the current turn with their lint result.
    """

    def __init__(self, root: Path):
        self.root = root
        self.context: dict[str, str] = {}
        self.reads: set[str] = set()
        self.used: set[str] = set()
        self.writes: list[str] = []
        self.commits: list[CommitRecord] = []

    def begin_session(self) -> None:
        self.context = {}

    def begin_turn(self) -> None:
        self.reads = set()
        self.used = set()
        self.writes = []
        self.commits = []

    def exists(self, rel: str) -> bool:
        return (self.root / rel).is_file()

    def read(self, rel: str) -> str:
        self.used.add(rel)
        if rel not in self.context:
            self.context[rel] = (self.root / rel).read_text(encoding="utf-8")
            self.reads.add(rel)
        return self.context[rel]

    def read_node(self, rel: str) -> tuple[dict, str]:
        return parse_frontmatter(self.read(rel))

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.context.pop(rel, None)
        self.writes.append(rel)

    def commit(self, subject: str) -> str:
        """One routine step as one commit, with the lint gate on the committed tree.

        Issue #28 asks for a green lint after every commit, not after every
        turn: turn 3 chains `create-food` and `log` inside one turn, so a
        commit that breaks the vault contract and a later commit that repairs
        it would both hide inside the turn. The gate sits here, on the single
        commit wrapper, so it holds for every commit of the run.

        The subject must read `<routine>: <one line>`. The lint reads a path,
        so the path must be the committed tree: the worktree is asserted
        clean, and no markdown file may be one git ignores, because such a
        file is in the worktree the lint reads and not in the commit. A lint
        error raises before the next routine step runs.
        """
        if not COMMIT_SUBJECT_RE.match(subject):
            raise Failed(f"commit subject is not `<routine>: <one line>`: {subject!r}")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--no-verify", "-m", subject)
        sha = git(self.root, "rev-parse", "--short", "HEAD")
        status = git(self.root, "status", "--porcelain")
        if status:
            raise Failed(f"the commit {subject!r} left the worktree dirty, so the lint cannot read the committed tree: "
                         f"{status.splitlines()[0]}")
        ignored = git(self.root, "status", "--porcelain", "--ignored=matching", "--", "*.md")
        if ignored:
            raise Failed(f"the commit {subject!r} left a markdown file git ignores, so the lint would read a file the "
                         f"commit does not hold: {ignored.splitlines()[0]}")
        errors = lint_vault(self.root)
        if errors:
            raise Failed(f"vault lint after the commit {subject!r} ({sha}): {errors[0]}")
        self.commits.append(CommitRecord(subject, sha))
        return sha


# --------------------------------------------------------------------------
# The scripted agent: the routines as they read on disk
# --------------------------------------------------------------------------

@dataclass
class Reply:
    lines: list[str]

    def text(self) -> str:
        return "\n".join(self.lines)


def _day_rel(date: str) -> str:
    return f"nodes/day/{date[:7]}/{date}.md"


def _insert_index_line(index_text: str, section: str, line: str) -> str:
    """Append one line to a `## <section>` of the Index, keeping the blank line before the next section."""
    lines = index_text.split("\n")
    start = lines.index(f"## {section}")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    body = lines[start + 1:end]
    while body and not body[-1].strip():
        body.pop()
    body.append(line)
    if end < len(lines):
        body.append("")
    return "\n".join(lines[:start + 1] + body + lines[end:])


class Agent:
    """The stand-in for the model: one method per routine the run needs."""

    def __init__(self, session: Session):
        self.session = session

    # -- helpers -----------------------------------------------------------

    def goals(self) -> tuple[dict[str, Decimal], dict[str, tuple[Decimal, Decimal]]]:
        data, _ = self.session.read_node("nodes/goals/Goals.md")
        goals = {macro: _decimal(data[key]) for macro, key in zip(SUMMARY_MACROS, MACROS)}
        bounds = {macro: (_decimal(data[f"{key}_min"]), _decimal(data[f"{key}_max"])) for macro, key in zip(SUMMARY_MACROS, MACROS)}
        return goals, bounds

    def node_rel(self, name: str, kind: str) -> str:
        return f"nodes/{kind}/{name}.md"

    def resolve(self, said: str, slot_word: bool = False):
        """The shared alias table of the Index; no name of this run is ambiguous, so the Pantry preference is not needed."""
        return resolve_name(said, parse_alias_table(self.session.read("index.md")), slot_word=slot_word)

    def foods_for(self, rels: Iterable[str]) -> dict[str, dict]:
        foods = {}
        for rel in rels:
            data, _ = self.session.read_node(rel)
            foods[data["name"]] = data
        return foods

    def grams_from_serving(self, food: Mapping[str, object], count: Decimal, unit: str) -> Decimal:
        """Router hard rule 1: convert a serving to grams before the write."""
        for serving in food.get("servings") or []:
            match = SERVING_PARTS_RE.match(serving)
            if match and match.group(2).rstrip("s") == unit.rstrip("s"):
                return count * _decimal(match.group(3)) / _decimal(match.group(1))
        raise AssertionError(f"[[{food['name']}]] has no serving `{unit}`")

    def read_day(self, date: str) -> tuple[dict, dict[str, list[str]]] | None:
        rel = _day_rel(date)
        if not self.session.exists(rel):
            return None
        data, body = self.session.read_node(rel)
        sections = _sections(body)
        entries = {slot: [line for line in sections.get(slot.capitalize(), []) if line.strip()] for slot in SLOTS
                   if slot.capitalize() in sections}
        return data, entries

    def day_totals(self, entries: Mapping[str, list[str]]) -> tuple[dict[str, Decimal], bool, dict[str, dict[str, int]], dict[str, int]]:
        """The seven exact totals over the entry nodes, the mark, the four-macro sum per slot and for the Day from the lines.

        The four Day macros are the sum of the whole numbers on the lines, as
        the spec fixes it; only fiber, sugar and salt are the exact node sum
        rounded once. The two can differ by one at a half.
        """
        exact = {key: Decimal(0) for key in TOTALS}
        marked = False
        slot_sums: dict[str, dict[str, int]] = {}
        meal_foods: dict[str, dict] = {}
        for slot, lines in entries.items():
            sums = {key: 0 for key in MACROS}
            for line in lines:
                entry = parse_entry_line(line)
                kind = "food" if self.session.exists(self.node_rel(entry.name, "food")) else "meal"
                node, _ = self.session.read_node(self.node_rel(entry.name, kind))
                if entry.change:
                    meal_foods.update(self.foods_for([self.node_rel(entry.change[0], "food")]))
                totals = entry_totals(node, entry.amount, entry.unit, meal_foods, entry.change)
                for key in TOTALS:
                    exact[key] += totals.exact[key]
                for key in MACROS:
                    sums[key] += entry.macros[key]
                marked = marked or entry.marked
            slot_sums[slot] = sums
        macros = {key: sum(sums[key] for sums in slot_sums.values()) for key in MACROS}
        return exact, marked, slot_sums, macros

    def render_day(self, date: str, status: str, entries: Mapping[str, list[str]], summary: list[str] | None,
                   exact: Mapping[str, Decimal], macros: Mapping[str, int], marked: bool) -> str:
        items: list[tuple[str, str | list[str]]] = [("type", "day"), ("name", date), ("date", date), ("status", status), ("goal", '"[[Goals]]"')]
        for key in MACROS:
            items.append((key, str(macros[key])))
        for key in NUTRIENTS:
            items.append((key, str(round_food_value(exact[key]))))
        items.append(("estimated", "true" if marked else "false"))
        parts = [render_frontmatter(items)]
        for slot in SLOTS:
            if entries.get(slot):
                parts.append(f"\n## {slot.capitalize()}\n\n" + "\n".join(entries[slot]) + "\n")
        if summary:
            parts.append("\n## Summary\n\n" + "\n".join(summary) + "\n")
        return "".join(parts)

    def write_state(self, today: str, open_day: str | None = None) -> None:
        """Router hard rule 5: `state.md` after every change, read fresh first. `open_day` None keeps the stored one."""
        data, _ = self.session.read_node("state.md")
        if open_day is None:
            open_day = data.get("open_day") or ""
            open_day = open_day[2:-2] if open_day.startswith("[[") else open_day
        text = render_frontmatter([("type", "state"), ("open_day", f'"[[{open_day}]]"' if open_day else '""'), ("updated", today)])
        self.session.write("state.md", text + "\n## Open items\n")

    def remaining_line(self, macros: Mapping[str, int], marked: bool) -> str:
        goals, _ = self.goals()
        self.session.read("routines/rebalance.md")
        parts = []
        for macro, key in zip(SUMMARY_MACROS, MACROS):
            left = goals[macro] - macros[key]
            parts.append(f"{'~' if marked else ''}{_num(abs(left))} {UNITS[macro]}{' over' if left < 0 else ''}")
        return "Left today: " + " · ".join(parts)

    # -- routines ------------------------------------------------------------

    def start_session(self) -> None:
        """ROUTER.md: read the Router, then the Index (no Context MCP here), then the State."""
        self.session.begin_session()
        self.session.read("ROUTER.md")
        self.session.read("index.md")
        self.session.read("state.md")

    def plan_today(self) -> Reply:
        """routines/rebalance.md step 3: before the first log, every open slot in full. Writes nothing."""
        self.session.read("routines/rebalance.md")
        goals, _ = self.goals()
        self.session.read("nodes/pantry/Pantry.md")
        meal, _ = self.session.read_node("nodes/meal/Usual breakfast.md")
        totals = entry_totals(meal, 1, "portion")
        macros = {key: round_total(totals.exact[key]) for key in MACROS}
        left = macro_line(dict(zip(MACROS, (goals[m] for m in SUMMARY_MACROS))))
        return Reply([
            f"Nothing logged yet, so all of today is left: {left}.",
            f"Breakfast: [[Usual breakfast]] = 1 portion — {macro_line(macros)}. All in the pantry.",
            "Lunch: [[Chicken breast]] 1 fillet (150 g) with [[Rice]] 2 portion (150 g), about 690 kcal · 48 P.",
            "Snack: [[Skyr]] 1 portion (200 g), about 130 kcal · 22 P.",
            "Dinner: [[Eggs]] 4 egg (240 g) with [[Rice]] 1 portion (75 g), about 600 kcal · 36 P.",
        ])

    def create_food(self, name: str, today: str, food: Mapping[str, str | list[str]]) -> tuple[Reply, str]:
        """routines/create-food.md: the Food at once, `reviewed: false`, its Index line, one commit."""
        self.session.read("routines/create-food.md")
        items: list[tuple[str, str | list[str]]] = [("type", "food"), ("name", name)]
        items.extend(food.items())
        items.extend([("source_date", today), ("reviewed", "false")])
        self.session.write(self.node_rel(name, "food"), render_frontmatter(items))
        aliases = ", ".join(food.get("aliases") or [])
        line = f"- [[{name}]] | {food['category']}" + (f" | {aliases}" if aliases else "")
        self.session.write("index.md", _insert_index_line(self.session.read("index.md"), "Food", line))
        self.write_state(today)
        sha = self.session.commit(f"create-food: {name}")
        reply = Reply([f"Created {name}: {food['kcal_per_100g']} kcal · {food['protein_g_per_100g']} P · {food['fat_g_per_100g']} F · "
                       f"{food['carbs_g_per_100g']} C /100 g ({food['number_source']}). Say ok to mark reviewed."])
        return reply, sha

    def log(self, date: str, clock: datetime.time, said: list[tuple], slot_word: str | None = None,
            new_foods: Mapping[str, Mapping] | None = None) -> tuple[Reply, list[str]]:
        """routines/log.md. `said` items are (name as said, amount, unit, guessed); unit `g`, `portion` or a serving unit."""
        self.session.read("state.md")
        self.session.read("routines/log.md")
        replies: list[str] = []
        shas: list[str] = []
        loaded = self.read_day(date)
        entries = dict(loaded[1]) if loaded else {}
        is_new = loaded is None
        slot = pick_slot(slot_word, clock, {s for s, lines in entries.items() if lines})
        named: list[str] = []
        for item in said:
            query, amount, unit, guessed = item
            resolution = self.resolve(query, slot_word=slot_word is not None)
            if resolution.status == "none":
                name = query.capitalize()
                reply, sha = self.create_food(name, date, (new_foods or {})[name])
                replies.extend(reply.lines)
                shas.append(sha)
                kind = "food"
            else:
                name, kind = resolution.name, resolution.kind
            node, _ = self.session.read_node(self.node_rel(name, kind))
            amount = _decimal(amount)
            if unit not in ("g", "portion"):
                amount, unit = self.grams_from_serving(node, amount, unit), "g"
            totals = entry_totals(node, amount, unit)
            macros = {key: round_total(totals.exact[key]) for key in MACROS}
            marked = totals.estimated or guessed
            entries.setdefault(slot, []).append(entry_line(name, _num(amount), unit, macros, marked))
            named.append(f"{name} {_num(amount)} {unit}")
            replies.append(f"Logged {slot}: {'~ ' if marked else ''}{name} {_num(amount)} {unit} — {macro_line(macros)}.")
        exact, day_marked, _, day_macros = self.day_totals(entries)
        if not is_new:
            self.session.read(_day_rel(date))
        self.session.write(_day_rel(date), self.render_day(date, "open", entries, None, exact, day_macros, day_marked))
        if is_new:
            self.write_state(date, open_day=date)
            index = self.session.read("index.md")
            month_line = f"- {date[:7]} | nodes/day/{date[:7]}/"
            if month_line not in index.split("\n"):
                self.session.write("index.md", _insert_index_line(index, "Day", month_line))
        shas.append(self.session.commit(f"log: {date} {slot} {', '.join(named)}"))
        replies.append(self.remaining_line(day_macros, day_marked))
        return Reply(replies), shas

    def no_snack(self, date: str) -> Reply:
        """routines/rebalance.md step 2: a removed slot lives in the chat. Writes nothing."""
        self.session.read("routines/rebalance.md")
        loaded = self.read_day(date)
        entries = loaded[1] if loaded else {}
        _, marked, _, macros = self.day_totals(entries)
        open_slots = [slot for slot in SLOTS if not entries.get(slot) and slot != "snack"]
        return Reply([f"Ok. Open slots today: {', '.join(open_slots)}.", self.remaining_line(macros, marked)])

    def suggest_lunch(self, date: str) -> Reply:
        """routines/rebalance.md steps 3 to 5: the next slot in full from the Pantry, protein first."""
        self.session.read("routines/rebalance.md")
        self.read_day(date)
        self.goals()
        self.session.read("nodes/pantry/Pantry.md")
        lines = ["Lunch (pantry only):"]
        total = {key: 0 for key in MACROS}
        for name, count, unit in (("Chicken breast", Decimal(1), "fillet"), ("Rice", Decimal(2), "portion")):
            food, _ = self.session.read_node(self.node_rel(name, "food"))
            grams = self.grams_from_serving(food, count, unit)
            macros = {key: round_total(value) for key, value in entry_totals(food, grams, "g").exact.items() if key in MACROS}
            for key in MACROS:
                total[key] += macros[key]
            lines.append(f"- [[{name}]] = {_num(count)} {unit} ({_num(grams)} g) — {macro_line(macros)}")
        lines.append(f"Lunch total: {macro_line(total)}.")
        lines.append("Dinner then needs about 45 P and 1000 kcal.")
        return Reply(lines)

    def close_day(self, date: str, hint: str | None) -> tuple[Reply, str]:
        """routines/close-day.md: the Summary, `status: closed`, the State cleared, one commit."""
        self.session.read("state.md")
        self.session.read("routines/close-day.md")
        data, entries = self.read_day(date)
        goals, bounds = self.goals()
        exact, marked, slot_sums, totals = self.day_totals(entries)
        summary = render_summary(slot_sums, totals, goals, bounds, marked, hint)
        words = verdict({m: _decimal(totals[k]) for m, k in zip(SUMMARY_MACROS, MACROS)}, bounds)
        self.session.read(_day_rel(date))
        self.session.write(_day_rel(date), self.render_day(date, "closed", entries, summary, exact, totals, marked))
        self.write_state(date, open_day="")
        sha = self.session.commit(f"close-day: {date} {words}")
        reply = [line for line in summary if line]
        reply.append(f"Unreviewed today: {', '.join(self.unreviewed_today(entries))}. Say ok to mark reviewed.")
        return Reply(reply), sha

    def unreviewed_today(self, entries: Mapping[str, list[str]]) -> list[str]:
        """routines/close-day.md step 7: the Day's Foods, the ingredient Foods of its Meals included, and its Meals, with `reviewed: false`, in the order eaten."""
        names: list[str] = []
        for lines in entries.values():
            for line in lines:
                name = parse_entry_line(line).name
                kind = "food" if self.session.exists(self.node_rel(name, "food")) else "meal"
                node, _ = self.session.read_node(self.node_rel(name, kind))
                candidates = [(name, node)]
                if kind == "meal":
                    candidates = [(food, self.session.read_node(self.node_rel(food, "food"))[0])
                                  for food in (re.match(r"\[\[([^\]]+)\]\]", item).group(1) for item in node["ingredients"])] + candidates
                for candidate, data in candidates:
                    if data.get("reviewed") == "false" and candidate not in names:
                        names.append(candidate)
        return names

    def review(self, today: datetime.date) -> Reply:
        """routines/review.md: this week from the Day files and Goals. Writes nothing."""
        self.session.read("routines/review.md")
        goals, _ = self.goals()
        monday = today - datetime.timedelta(days=today.weekday())
        days = []
        for offset in range((today - monday).days + 1):
            date = (monday + datetime.timedelta(days=offset)).isoformat()
            loaded = self.read_day(date)
            if loaded is None:
                continue
            data, entries = loaded
            words = None
            if data["status"] != "open":
                lines = [line.strip() for line in _sections(self.session.read_node(_day_rel(date))[1])["Summary"] if line.strip()]
                words = next(line for line in lines if line == "on target" or line.startswith("off target:"))
            days.append(DaySummary(date, data["status"], data["estimated"] == "true", {key: _decimal(data[key]) for key in TOTALS}, words))
        return Reply(review_reply(days, goals, today))


# --------------------------------------------------------------------------
# The run: turns, assertions, the throwaway branch
# --------------------------------------------------------------------------

@dataclass
class TurnReport:
    number: int
    said: str
    reads: int
    used: int
    wrote: list[str]
    commits: list[CommitRecord]
    reply: list[str]


@dataclass
class Report:
    branch: str
    turns: list[TurnReport] = field(default_factory=list)
    commit_subjects: list[str] = field(default_factory=list)
    ok: bool = False
    error: str | None = None


CROISSANT = {
    "aliases": ["Kipferl", "Buttercroissant"],
    "category": "grain",
    "kcal_per_100g": "406",
    "protein_g_per_100g": "8",
    "fat_g_per_100g": "21",
    "carbs_g_per_100g": "46",
    "fiber_g_per_100g": "2",
    "sugar_g_per_100g": "6",
    "salt_g_per_100g": "1",
    "label_basis": "100g",
    "number_source": "database",
    "source_ref": "Swiss Food Composition Database, Croissant",
}
"""The unknown Food of turn 3, numbers and aliases from the prototype branch."""

GOAL_LINE = "Goal 2500 kcal (2375-2625), 135 P (128-142), 60 F (57-63), 355 C (337-373)."
LINE_USUAL = "- [[Usual breakfast]] = 1 portion — 540 kcal · 46 P · 7 F · 67 C"
LINE_CROISSANT = "- ~ [[Croissant]] = 60 g — 244 kcal · 5 P · 13 F · 28 C"
LINE_CHICKEN = "- [[Chicken breast]] = 200 g — 214 kcal · 49 P · 2 F · 0 C"
LINE_RICE = "- [[Rice]] = 150 g — 528 kcal · 11 P · 1 F · 117 C"
LINE_EGGS = "- [[Eggs]] = 240 g — 336 kcal · 30 P · 24 F · 1 C"
VERDICT = "off target: kcal low, fat low, carbs low"
HINT = "Fat and carbs sit low; keep the snack and add a grain at dinner."


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise Failed(message)


class Run:
    def __init__(self, vault: Path, monday: datetime.date, out: Callable[[str], None]):
        self.vault = vault
        self.day1 = monday.isoformat()
        self.day2 = (monday + datetime.timedelta(days=1)).isoformat()
        self.out = out
        self.session = Session(vault)
        self.agent = Agent(self.session)
        self.head = git(vault, "rev-parse", "HEAD")
        self.day1_closed_text: str | None = None

    # -- file readers for the assertions (outside the agent's budget) ------

    def text(self, rel: str) -> str:
        return (self.vault / rel).read_text(encoding="utf-8")

    def node(self, rel: str) -> tuple[dict, dict[str, list[str]]]:
        data, body = parse_frontmatter(self.text(rel))
        return data, {k: [line for line in v if line.strip()] for k, v in _sections(body).items()}

    def frontmatter(self, rel: str) -> dict:
        return parse_frontmatter(self.text(rel))[0]

    def new_commits(self) -> list[str]:
        subjects = git(self.vault, "log", "--format=%s", f"{self.head}..HEAD")
        self.head = git(self.vault, "rev-parse", "HEAD")
        return [s for s in reversed(subjects.split("\n")) if s]

    def check_day_totals(self, rel: str, kcal: int, protein: int, fat: int, carbs: int, estimated: bool) -> None:
        data = self.frontmatter(rel)
        got = tuple(int(data[key]) for key in MACROS)
        expect(got == (kcal, protein, fat, carbs), f"{rel} totals are {got}, expected {(kcal, protein, fat, carbs)}")
        expect(data["estimated"] == ("true" if estimated else "false"), f"{rel} `estimated` is {data['estimated']}")

    def check_clean(self) -> None:
        expect(git(self.vault, "status", "--porcelain") == "", "the worktree has uncommitted changes")

    # -- the turns --------------------------------------------------------

    def turns(self) -> list[tuple[str, str, Callable[[], object], Callable[[object, list[str]], None]]]:
        a, d1, d2 = self.agent, self.day1, self.day2
        t = datetime.time

        def check_plan(reply, commits):
            expect(commits == [], "plan today made a commit")
            expect("2500 kcal · 135 P · 60 F · 355 C" in reply.lines[0], "the plan does not start from the full targets")
            expect(all(word in reply.text() for word in ("Breakfast", "Lunch", "Snack", "Dinner")), "the plan misses an open slot")

        def check_breakfast(reply, commits):
            expect(commits == [f"log: {d1} breakfast Usual breakfast 1 portion"], f"commits {commits}")
            data, sections = self.node(_day_rel(d1))
            expect(sections.get("Breakfast") == [LINE_USUAL], f"Breakfast lines {sections.get('Breakfast')}")
            expect(data["status"] == "open", "the new Day is not open")
            self.check_day_totals(_day_rel(d1), 540, 46, 7, 67, estimated=False)
            expect(self.frontmatter("state.md")["open_day"] == f"[[{d1}]]", "state.md open_day is not the new Day")
            expect(f"- {d1[:7]} | nodes/day/{d1[:7]}/" in self.text("index.md"), "index.md has no month line")
            expect(reply.lines[0].startswith("Logged breakfast:"), "the reply does not name the slot")

        def check_croissant(reply, commits):
            expect(commits == ["create-food: Croissant", f"log: {d1} breakfast Croissant 60 g"], f"commits {commits}")
            food = self.frontmatter("nodes/food/Croissant.md")
            expect(food["reviewed"] == "false", "Croissant is not unreviewed")
            expect("- [[Croissant]] | grain | Kipferl, Buttercroissant" in self.text("index.md").split("\n"), "no Index line for Croissant")
            _, sections = self.node(_day_rel(d1))
            expect(sections["Breakfast"] == [LINE_USUAL, LINE_CROISSANT], f"Breakfast lines {sections['Breakfast']}")
            self.check_day_totals(_day_rel(d1), 784, 51, 20, 95, estimated=True)
            expect("Say ok to mark reviewed." in reply.lines[0], "the create reply lacks the ok line")
            expect("~ Croissant" in reply.lines[1], "the log reply does not carry the mark")

        def check_no_snack(reply, commits):
            expect(commits == [], "no snack today made a commit")
            expect(reply.lines[0] == "Ok. Open slots today: lunch, dinner.", reply.lines[0])

        def check_suggestion(reply, commits):
            expect(commits == [], "the suggestion made a commit")
            expect(reply.lines[1] == "- [[Chicken breast]] = 1 fillet (150 g) — 161 kcal · 37 P · 2 F · 0 C", reply.lines[1])
            expect(reply.lines[2] == "- [[Rice]] = 2 portion (150 g) — 528 kcal · 11 P · 1 F · 117 C", reply.lines[2])

        def check_lunch(reply, commits):
            expect(commits == [f"log: {d1} lunch Chicken breast 200 g, Rice 150 g"], f"commits {commits}")
            _, sections = self.node(_day_rel(d1))
            expect(sections["Lunch"] == [LINE_CHICKEN, LINE_RICE], f"Lunch lines {sections['Lunch']}")
            expect(list(sections)[:2] == ["Breakfast", "Lunch"], f"slot order {list(sections)}")
            self.check_day_totals(_day_rel(d1), 1526, 111, 23, 212, estimated=True)

        def check_dinner(reply, commits):
            expect(commits == [f"log: {d1} dinner Eggs 240 g"], f"commits {commits}")
            data, sections = self.node(_day_rel(d1))
            expect(sections["Dinner"] == [LINE_EGGS], f"Dinner lines {sections['Dinner']}")
            self.check_day_totals(_day_rel(d1), 1862, 141, 47, 213, estimated=True)
            expect((data["fiber_g"], data["sugar_g"], data["salt_g"]) == ("11.8", "35.2", "2.2"), "nutrient totals differ")
            expect("Summary" not in sections, "an open Day has a Summary")

        def check_close(reply, commits):
            expect(commits == [f"close-day: {d1} {VERDICT}"], f"commits {commits}")
            data, sections = self.node(_day_rel(d1))
            expect(data["status"] == "closed", "the Day is not closed")
            expect(sections["Summary"] == [
                SUMMARY_TABLE_HEADER, SUMMARY_SEPARATOR,
                "| breakfast | ~784 | ~51 | ~20 | ~95 |",
                "| lunch | ~742 | ~60 | ~3 | ~117 |",
                "| dinner | ~336 | ~30 | ~24 | ~1 |",
                "| TOTAL | ~1862 | ~141 | ~47 | ~213 |",
                GOAL_LINE,
                "- kcal 638 under", "- protein 6 over", "- fat 13 under", "- carbs 142 under",
                VERDICT,
                f"Hint: {HINT}",
            ], "Summary:\n" + "\n".join(sections["Summary"]))
            expect(self.frontmatter("state.md")["open_day"] == "", "state.md still names an open Day")
            expect(reply.lines[-1] == "Unreviewed today: Skyr, Blueberries, Oats, Soy milk Milsani, Croissant, Chicken breast, Rice, Eggs. "
                   "Say ok to mark reviewed.", reply.lines[-1])
            self.day1_closed_text = self.text(_day_rel(d1))

        def check_next_day(reply, commits):
            expect(commits == [f"log: {d2} breakfast Usual breakfast 1 portion"], f"commits {commits}")
            expect(self.text(_day_rel(d1)) == self.day1_closed_text, f"{d1} changed after its close")
            data, sections = self.node(_day_rel(d2))
            expect(data["status"] == "open" and sections.get("Breakfast") == [LINE_USUAL], f"{d2} is not a fresh open Day")
            expect(self.frontmatter("state.md")["open_day"] == f"[[{d2}]]", "state.md does not name the new Day")

        def check_review(reply, commits):
            expect(commits == [], "the review made a commit")
            expect(reply.lines == [
                "Days: 1 of 2 closed, 0 auto-closed, missing none",
                "Average: ~1862 kcal · ~141 P · ~47 F · ~213 C · ~11.8 fiber · ~35.2 sugar · ~2.2 salt",
                "Target: 2500 kcal · 135 P · 60 F · 355 C",
                "On target: 0 of 1",
                "Most common miss: kcal low, 1 days; fat low, 1 days; carbs low, 1 days",
                f"{d2} is open and not counted.",
            ], "review:\n" + reply.text())
            expect(len(reply.lines) < 10, "the review reply has ten lines or more")

        def new_session_then(action):
            def go():
                a.start_session()
                return action()
            return go

        return [
            ("08:10", "Plan today for me.", new_session_then(a.plan_today), check_plan),
            ("08:30", "I had the usual breakfast.", lambda: a.log(d1, t(8, 30), [("usual", 1, "portion", False)]), check_breakfast),
            ("10:15", "Also ate a croissant at the office, count it as breakfast.",
             lambda: a.log(d1, t(10, 15), [("croissant", 60, "g", True)], slot_word="breakfast", new_foods={"Croissant": CROISSANT}),
             check_croissant),
            ("12:40", "No snack today.", lambda: a.no_snack(d1), check_no_snack),
            ("12:45", "What should I eat for lunch?", lambda: a.suggest_lunch(d1), check_suggestion),
            ("13:30", "Had that, but 200 g of chicken.", lambda: a.log(d1, t(13, 30), [("chicken", 200, "g", False), ("rice", 150, "g", False)]),
             check_lunch),
            ("19:30", "Dinner: 4 eggs.", lambda: a.log(d1, t(19, 30), [("eggs", 4, "egg", False)], slot_word="dinner"), check_dinner),
            ("21:00", "Close the day.", lambda: a.close_day(d1, HINT), check_close),
            (f"{d2} 08:20", "breakfast: the usual",
             new_session_then(lambda: a.log(d2, t(8, 20), [("the usual", 1, "portion", False)], slot_word="breakfast")), check_next_day),
            (f"{d2} 08:25", "How was my week?", lambda: a.review(datetime.date.fromisoformat(d2)), check_review),
        ]

    def preconditions(self) -> None:
        for rel in ("nodes/meal/Usual breakfast.md", "nodes/food/Chicken breast.md", "nodes/food/Rice.md", "nodes/food/Eggs.md",
                    "nodes/goals/Goals.md", "nodes/pantry/Pantry.md"):
            expect((self.vault / rel).is_file(), f"the run needs {rel}")
        expect(not (self.vault / "nodes/food/Croissant.md").exists(), "Croissant exists already; the run creates it")
        for date in (self.day1, self.day2):
            expect(not (self.vault / _day_rel(date)).exists(), f"{_day_rel(date)} exists; pick another week with --date")
        expect(self.frontmatter("state.md")["open_day"] == "", "state.md names an open Day; the run needs a vault with none")
        goals = self.frontmatter("nodes/goals/Goals.md")
        expect(tuple(goals[k] for k in ("kcal", "protein_g", "fat_g", "carbs_g", "tolerance_pct")) == ("2500", "135", "60", "355", "5"),
               "the Goals differ from the seed 2500 / 135 / 60 / 355 at 5 %; the fixed lines of this run assume it")
        errors = lint_vault(self.vault)
        expect(not errors, f"vault lint of the start state: {errors[0] if errors else ''}")

    def execute(self, report: Report) -> None:
        self.preconditions()
        for number, (clock, said, action, check) in enumerate(self.turns(), start=1):
            self.session.begin_turn()
            result = action()
            reply = result[0] if isinstance(result, tuple) else result
            commits = self.new_commits()
            records = list(self.session.commits)
            expect([record.subject for record in records] == commits,
                   f"turn {number} recorded {[r.subject for r in records]} but git holds {commits}")
            expect(len(self.session.reads) < READ_BUDGET, f"turn {number} read {len(self.session.reads)} files")
            self.check_clean()
            check(reply, commits)
            report.commit_subjects.extend(commits)
            turn = TurnReport(number, said, len(self.session.reads), len(self.session.used), list(self.session.writes), records, reply.lines)
            report.turns.append(turn)
            self.out(f"\n## Turn {number} · {clock} · \"{said}\"")
            self.out(f"Read: {turn.reads} files from disk ({turn.used} in use): {', '.join(sorted(self.session.reads)) or 'nothing'}")
            self.out(f"Wrote: {', '.join(dict.fromkeys(turn.wrote)) or 'nothing'}")
            for record in records:
                self.out(f"Commit: {record.subject} ({record.sha}) — lint ok")
            self.out("Said:")
            for line in reply.lines:
                self.out(f"> {line}")
            self.out("Asserted: files, a clean worktree, the lint after every commit, reads under budget")


def run(repo: Path, monday: datetime.date, keep: bool = False, out: Callable[[str], None] = print) -> Report:
    """Run the seeded day on a throwaway branch in a temporary worktree of `repo`. Never touches `main`."""
    repo = Path(repo).resolve()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"{BRANCH_PREFIX}{stamp}"
    main_before = git(repo, "rev-parse", "--verify", "--quiet", "main") if _has_branch(repo, "main") else None
    worktree = Path(tempfile.mkdtemp(prefix="seeded-day-"))
    report = Report(branch)
    out(f"# Seeded-day acceptance run · {monday.isoformat()} and the next day · branch {branch}")
    git(repo, "worktree", "add", "-q", "-b", branch, str(worktree), "HEAD")
    try:
        Run(worktree, monday, out).execute(report)
        report.ok = True
    except AssertionError as exc:
        report.error = str(exc)
    finally:
        if keep:
            out(f"\nKept: worktree {worktree} on branch {branch}. Remove with `git worktree remove {worktree}` and `git branch -D {branch}`.")
        else:
            git(repo, "worktree", "remove", "--force", str(worktree))
            git(repo, "branch", "-D", "-q", branch)
            out(f"\nRemoved: the worktree and branch {branch}. Nothing was pushed.")
    if main_before is not None and git(repo, "rev-parse", "main") != main_before:
        report.ok, report.error = False, "main moved during the run"
    if report.ok:
        out(f"PASS: {len(report.turns)} turns, {len(report.commit_subjects)} commits, lint green after every commit.")
    else:
        out(f"FAIL: {report.error}")
    return report


def _has_branch(repo: Path, name: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", name], capture_output=True).returncode == 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Seeded-day acceptance run on a throwaway branch.")
    parser.add_argument("--date", type=datetime.date.fromisoformat, default=None,
                        help="the Monday of the seeded week (default: Monday of the current week)")
    parser.add_argument("--keep", action="store_true", help="keep the worktree and branch for inspection")
    args = parser.parse_args(argv[1:])
    date = args.date or datetime.date.today()
    monday = date - datetime.timedelta(days=date.weekday())
    report = run(Path(__file__).resolve().parent.parent, monday, keep=args.keep)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
