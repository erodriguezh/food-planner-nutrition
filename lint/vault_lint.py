#!/usr/bin/env python3
"""Vault lint for the food planner vault.

Run from the repository root:

    python3 lint/vault_lint.py

Exit code 0 when the vault is clean, 1 on the first violation. The checks run
in a fixed order (nodes load, common conventions, node locations, Goals, Foods,
Meals, Days, Pantry, Router, State, Index, routines), files in sorted path
order, so the first violation is deterministic.
No dependencies beyond the Python 3 standard library.

Checks (v3):
- every node under nodes/ has flat YAML frontmatter with core types only
- every node has `type` and `name`; `name` equals the file base name;
  base names are unique across the vault
- no file outside nodes/ carries node frontmatter
- the Goals node follows its schema; bounds use the rounding rule
- every Food sits directly at nodes/food/<Name>.md and has its required
  properties and enums, numbers with at most one decimal, servings in grams,
  density fields with a 100ml label basis, a `label_name` that is one of the
  aliases, `estimated_from` as a quoted link to a Food and present whenever
  `number_source` is `estimate`, no unknown property, and a body that is empty
  or holds one `## Notes` section with no text outside it
- every Meal sits directly at nodes/meal/<Name>.md and has its required
  properties, slots as slot words, ingredients as `"[[Food]] = <grams> g"` one
  per Food, `weight_g` equal to the ingredient sum, the seven totals within
  the rounding of the sum over the Food nodes, `estimated` true exactly when
  an ingredient Food is an estimate, and a body of Prepare and Notes only
- every Day sits at nodes/day/<YYYY-MM>/<date>.md with name and date equal to
  the file name, its required properties, `goal` as the Goals link, slot
  sections in the fixed order with canonical entry lines (the `~` right after
  the bullet, the ingredient change by portion), the mark on every estimated
  Food or Meal, the four totals equal to the sum of the lines, `estimated`
  true exactly when a line is marked; an open Day also matches its nodes
- exactly one Pantry node sits at nodes/pantry/Pantry.md
- the Pantry node has `updated`, staples as `"[[Food]]"`, items as
  `"[[Food or Meal]]"` with a grams, portion or cooked-grams amount and an
  optional `until` date; every link resolves by canonical name
- ROUTER.md is under 500 tokens
- state.md has its fields and names the one open Day; Open items holds no
  unreviewed Food lines
- index.md has one section per node type and no line without a node; every
  Food has exactly one line with its category and all aliases plus the label
  name; every Meal has exactly one line with its slots (or `any`) and all
  aliases; every Day month folder has exactly one month line
- every routine file has the five sections and is under 300 tokens
"""
from __future__ import annotations

import difflib
import math
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

NODE_TYPES = ("food", "meal", "day", "goals", "pantry")
INDEX_SECTIONS = ("Food", "Meal", "Day", "Goals", "Pantry")
ROUTINE_SECTIONS = ("When", "Read", "Steps", "Write", "Reply")
ROUTER_TOKEN_LIMIT = 500
ROUTINE_TOKEN_LIMIT = 300
MACROS = ("kcal", "protein_g", "fat_g", "carbs_g")

FOOD_CATEGORIES = ("protein", "dairy", "grain", "vegetable", "fruit", "fat", "snack", "drink")
LABEL_BASES = ("100g", "100ml")
NUMBER_SOURCES = ("label", "database", "estimate")
FOOD_MACROS = ("kcal_per_100g", "protein_g_per_100g", "fat_g_per_100g", "carbs_g_per_100g")
FOOD_REQUIRED = ("type", "name", "category") + FOOD_MACROS + ("label_basis", "number_source", "source_date", "reviewed")
FOOD_NUTRIENTS = ("fiber_g_per_100g", "sugar_g_per_100g", "salt_g_per_100g")
FOOD_OPTIONAL_NUMBERS = FOOD_NUTRIENTS + ("density_g_per_ml",)
FOOD_OPTIONAL = ("aliases", "label_name", "brand", "servings", "density_source", "source_ref", "barcode", "estimated_from") + FOOD_OPTIONAL_NUMBERS
PANTRY_REQUIRED = ("type", "name", "updated")
PANTRY_OPTIONAL = ("staples", "items")
CHECKBOX_VALUES = ("true", "false")

SLOTS = ("breakfast", "lunch", "snack", "dinner")
SLOT_HEADINGS = tuple(slot.capitalize() for slot in SLOTS)
DAY_STATUSES = ("open", "closed", "auto-closed")
NUTRIENTS = ("fiber_g", "sugar_g", "salt_g")
TOTALS = MACROS + NUTRIENTS
MEAL_REQUIRED = ("type", "name", "ingredients", "portions", "weight_g") + TOTALS + ("totals_date", "estimated", "reviewed")
MEAL_OPTIONAL = ("aliases", "slots", "cooked_weight_g")
MEAL_BODY_SECTIONS = ("Prepare", "Notes")
DAY_REQUIRED = ("type", "name", "date", "status", "goal") + TOTALS + ("estimated",)
DAY_BODY_SECTIONS = SLOT_HEADINGS + ("Summary", "Notes")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s+(.*))?$")
INDEX_LINK_LINE_RE = re.compile(r"^- \[\[([^\]]+)\]\](?: \| .*)?$")
INDEX_DAY_LINE_RE = re.compile(r"^- (\d{4}-\d{2}) \| (nodes/day/\d{4}-\d{2}/)$")
SERVING_RE = re.compile(r"^\d+(\.\d+)? [A-Za-z][A-Za-z ]* = \d+(\.\d+)? g$")
QUOTED_LINK_RE = re.compile(r"^\[\[([^\]|#]+)\]\]$")
PANTRY_ITEM_RE = re.compile(r"^\[\[([^\]|#]+)\]\](?: = ([^,]+?))?(?:, until (\d{4}-\d{2}-\d{2}))?$")
FOOD_AMOUNT_RE = re.compile(r"^\d+(\.\d+)? g$")
MEAL_AMOUNT_RE = re.compile(r"^\d+(\.\d+)? (portion|g cooked)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
INGREDIENT_RE = re.compile(r"^\[\[([^\]|#]+)\]\] = (\d+(?:\.\d+)?) g$")
# `- [[Name]] = <n> g|portion — <kcal> kcal · <P> P · <F> F · <C> C`, with an
# optional `~ ` right after the bullet and an optional ingredient change
# `, [[Food]] = <n> g` after the amount.
ENTRY_LINE_RE = re.compile(
    r"^- (~ )?\[\[([^\]|#]+)\]\] = (\d+(?:\.\d+)?) (g|portion)"
    r"(?:, \[\[([^\]|#]+)\]\] = (\d+(?:\.\d+)?) g)?"
    r" — (\d+) kcal · (\d+) P · (\d+) F · (\d+) C$"
)


# --------------------------------------------------------------------------
# Rules stated once and applied everywhere
# --------------------------------------------------------------------------

def _decimal(value) -> Decimal:
    """The number as written, not as the binary float approximates it.

    `str()` gives the shortest decimal that round-trips, so a computed 0.35
    stays 0.35 and rounds half up to 0.4 instead of down to 0.3.
    """
    return Decimal(str(value))


def _half_up(value: float) -> int:
    """Nearest whole number, a half rounds up. Shared by the two whole-number rules."""
    return int(_decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def round_bound(value: float) -> int:
    """Rounding rule for Goals bounds: nearest whole number, a half rounds up.

    The rule is stated for the agent in routines/goals.md step 4. This is the
    lint's application of it.
    """
    return _half_up(value)


def compute_bounds(targets: dict, tolerance_pct: float) -> dict:
    """The eight stored bounds for the four targets, rounded with round_bound()."""
    tolerance = tolerance_pct / 100
    bounds = {}
    for macro in MACROS:
        bounds[f"{macro}_min"] = round_bound(targets[macro] * (1 - tolerance))
        bounds[f"{macro}_max"] = round_bound(targets[macro] * (1 + tolerance))
    return bounds


DEFAULT_TOLERANCE_PCT = 5


def apply_goal_change(existing: dict | None, stated_targets: dict, stated_tolerance_pct: float | None, today: str) -> dict:
    """The goals routine as a function: the Goals frontmatter after one chat change.

    First setup (no existing node): every one of the four targets must be
    stated; tolerance defaults to 5. Existing node: targets and tolerance the
    user did not state keep their stored values. Every change recomputes all
    eight bounds and rewrites `since`.
    """
    if existing is None:
        missing = [m for m in MACROS if m not in stated_targets]
        if missing:
            raise ValueError(f"first setup needs all four targets; missing {missing}")
        targets = {m: stated_targets[m] for m in MACROS}
        tolerance = DEFAULT_TOLERANCE_PCT if stated_tolerance_pct is None else stated_tolerance_pct
    else:
        targets = {m: stated_targets.get(m, float(existing[m])) for m in MACROS}
        tolerance = float(existing["tolerance_pct"]) if stated_tolerance_pct is None else stated_tolerance_pct
    result = {"type": "goals", "name": "Goals"}
    result.update(targets)
    result["tolerance_pct"] = tolerance
    result.update(compute_bounds(targets, tolerance))
    result["since"] = today
    return result


def estimate_tokens(text: str) -> int:
    """Token estimate used for the Router limit: one token per four characters."""
    return math.ceil(len(text) / 4)


# --------------------------------------------------------------------------
# create-food routine as functions
# --------------------------------------------------------------------------

def round_food_value(value: float) -> float:
    """Rounding rule for Food numbers: one decimal, a half rounds up (2.25 -> 2.3).

    Stated for the agent in routines/create-food.md step 3. A whole result is
    returned as an int so `64.0` is written `64`.
    """
    rounded = float(_decimal(value).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    return int(rounded) if rounded == int(rounded) else rounded


def per_100g_from_per_100ml(values: dict, density_g_per_ml: float) -> dict:
    """Convert per-100-ml label values to per 100 g once, at creation.

    100 ml weigh 100 × density grams, so a per-100-g value is the per-100-ml
    value divided by the density. Every result uses round_food_value().
    """
    return {key: round_food_value(float(value) / density_g_per_ml) for key, value in values.items()}


def mark_reviewed(data: dict) -> dict:
    """The "ok" step: a copy of the Food frontmatter with `reviewed: true` and nothing else changed.

    `number_source` stays as it is; review never removes an estimate mark.
    """
    result = dict(data)
    result["reviewed"] = "true"
    return result


# --------------------------------------------------------------------------
# Alias resolution as a function (shared Food and Meal table from the Index)
# --------------------------------------------------------------------------

_UMLAUTS = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "ss", "é": "e", "è": "e"})
FUZZY_CUTOFF = 0.8


def normalize_alias(text: str) -> str:
    """Case-insensitive, umlaut-free, plural-tolerant form of a name or alias.

    Plurals: a trailing `n` is dropped (Heidelbeeren -> heidelbeere), else a
    trailing `es`, else a trailing `s` (eggs -> egg). Both sides of a match
    are normalized the same way, so the rule needs no dictionary.
    """
    text = " ".join(text.casefold().translate(_UMLAUTS).split())
    if len(text) > 3:
        if text.endswith("n"):
            text = text[:-1]
        elif text.endswith("es"):
            text = text[:-2]
        elif text.endswith("s"):
            text = text[:-1]
    return text


@dataclass
class Resolution:
    """Result of resolve_name() or resolve_label().

    resolve_name() statuses: exact, alias, fuzzy, ambiguous, none.
    resolve_label() has three statuses of its own and never returns any
    resolve_name() status: `barcode` and `label` name the one existing Food the
    package identifies, and `new` names the Food to create. One `label` status
    covers all three label-name stages, because the label path reuses a Food
    only when the identity leaves exactly one, so which stage matched changes
    nothing the caller does. resolve_label() never returns ambiguous or none.

    `candidates` holds the sorted canonical names the winning stage found: every
    candidate for a resolve_name() status, the one winner for `barcode` and
    `label`, and for `new` the existing names that hold the base name the label
    printed. It is empty only for status `none` and for a `new` name that took
    no existing base name. `kind` is `food` or `meal`, the kind of the one winner;
    it is None when there is no winner (`ambiguous`, `none`).
    """
    status: str
    name: str | None = None
    candidates: tuple[str, ...] = ()
    kind: str | None = None


def parse_alias_table(index_text: str) -> list[tuple[str, str, list[str]]]:
    """The shared alias table from index.md: (canonical name, food|meal, aliases) per line."""
    table = []
    for section, lines in _sections(index_text).items():
        if section not in ("Food", "Meal"):
            continue
        for line in lines:
            match = INDEX_LINK_LINE_RE.match(line)
            if not match:
                continue
            fields = [f.strip() for f in line.split(" | ")]
            aliases = [a.strip() for a in fields[2].split(",") if a.strip()] if len(fields) > 2 else []
            table.append((match.group(1), section.lower(), aliases))
    return table


def resolve_name(query: str, table: list[tuple[str, str, list[str]]], pantry_names: list[str] | tuple[str, ...] = (),
                 slot_word: bool = False) -> Resolution:
    """Resolve what the user said to one canonical name, as routines/create-food.md describes.

    Order: exact canonical name, then alias, then fuzzy. Fuzzy candidates are
    the union of every close match above FUZZY_CUTOFF and the forms that start
    with or contain what the user said; the close-match half has no maximum
    count, so a late close candidate is never dropped in silence.
    One candidate is used (the reply names a fuzzy one).
    Several candidates of one kind: prefer the single one in the Pantry; else
    ask (status `ambiguous`). Nothing close: status `none`.

    Every candidate keeps its kind (`food` or `meal`). A Food and a Meal in the
    same winning stage always ask, as spec #22 requires: a Pantry item can be a
    Food or a Meal, so the Pantry preference must not decide a cross-kind
    collision. The one exception (story 49, ticket #25): `slot_word` is true
    when the log carries a slot word ("breakfast: usual"), and then the Meal
    candidates of the stage win over the Food ones. Two Meals still follow the
    same-kind rule: one Pantry Meal wins, else the agent asks.

    The stage order comes first, so the ask is a same-stage rule: the first
    matching stage stops the search, and a name that is exact for one kind beats
    an alias of the other kind without a question. Only the candidates of the
    one matching stage can collide.

    Normalization can map two different canonical names to one form (case,
    umlauts, plurals). Every stage therefore keeps a set of candidates per
    normalized form, so a second candidate is never discarded in silence.
    """
    stage, hits = _stage_candidates(query, table)
    if stage is None:
        return Resolution("none")
    if slot_word:
        meals = {hit for hit in hits if hit[1] == "meal"}
        if meals:
            hits = meals
    return _one_or_ask(stage, hits, pantry_names)


def _stage_candidates(query: str, table: list[tuple[str, str, list[str]]]) -> tuple[str | None, set[tuple[str, str]]]:
    """The first matching stage and every (canonical name, kind) it found.

    Stages in order: exact canonical name, then alias, then fuzzy. The first
    stage with a candidate wins and stops the search. Nothing close: (None, an
    empty set).

    No preference is applied here: the caller decides what several candidates
    of one stage mean. resolve_name() hands them to _one_or_ask(), which may
    prefer the one Pantry candidate. resolve_label() must not, so it filters
    them by the printed package identity instead.
    """
    wanted = normalize_alias(query)
    name_forms = _group_by_normalized_form((name, name, kind) for name, kind, _aliases in table)
    if wanted in name_forms:
        return "exact", name_forms[wanted]
    alias_forms = _group_by_normalized_form(
        (alias, name, kind) for name, kind, aliases in table for alias in aliases
    )
    if wanted in alias_forms:
        return "alias", alias_forms[wanted]
    forms = _group_by_normalized_form(
        (form, name, kind) for name, kind, aliases in table for form in [name] + list(aliases)
    )
    # n=len(forms) keeps every form above the cutoff: a fixed maximum would
    # drop a late close candidate in silence and could name a wrong winner.
    # get_close_matches() needs n > 0, so an empty table finds nothing.
    close = set(difflib.get_close_matches(wanted, list(forms), n=len(forms), cutoff=FUZZY_CUTOFF)) if forms else set()
    close |= {form for form in forms if form.startswith(wanted) or wanted in form}
    fuzzy_hits = {hit for form in close for hit in forms[form]}
    if not fuzzy_hits:
        return None, set()
    return "fuzzy", fuzzy_hits


def _group_by_normalized_form(triples: Iterable[tuple[str, str, str]]) -> dict[str, set[tuple[str, str]]]:
    """Map each normalized form to the set of (canonical name, kind) it produces."""
    forms: dict[str, set[tuple[str, str]]] = {}
    for form, name, kind in triples:
        forms.setdefault(normalize_alias(form), set()).add((name, kind))
    return forms


def _one_or_ask(status: str, hits: set[tuple[str, str]], pantry_names: Iterable[str]) -> Resolution:
    """Use the one candidate; else the one Pantry candidate of one kind; else ask.

    Mixed kinds always ask: the Pantry preference never decides a Food-versus-Meal
    collision (spec #22).
    """
    by_name = {name: kind for name, kind in hits}
    candidates = tuple(sorted(by_name))
    kinds = {kind for _name, kind in hits}
    if len(kinds) > 1:
        return Resolution("ambiguous", None, candidates)
    if len(candidates) == 1:
        return Resolution(status, candidates[0], candidates, by_name[candidates[0]])
    in_pantry_set = set(pantry_names)
    in_pantry = [name for name in candidates if name in in_pantry_set]
    if len(in_pantry) == 1:
        return Resolution(status, in_pantry[0], candidates, by_name[in_pantry[0]])
    return Resolution("ambiguous", None, candidates)


@dataclass
class LabelIdentity:
    """What a label photo gives about the product: printed name, brand, barcode.

    `label_name` is the name as printed, often in German. `brand` and `barcode`
    are absent on a label that does not print them.
    """
    label_name: str
    brand: str | None = None
    barcode: str | None = None


def resolve_label(
    label: LabelIdentity | Mapping[str, str | None],
    table: list[tuple[str, str, list[str]]],
    foods: Iterable[Mapping[str, object]] = (),
) -> Resolution:
    """Resolve a label photo to one Food, with no question, as routines/create-food.md describes.

    Issue #24: "A label photo produces a Food node ... with no question asked."
    The shared resolve_name() asks on a Food-versus-Meal collision and on two
    candidates of one kind. A label carries its own identity, so this function
    decides alone: it never returns `ambiguous` and never returns `none`, and
    its winner is always a Food.

    The package identity alone decides. There is no Pantry parameter, because
    Pantry membership is not package identity: the ordinary chat resolution may
    break a same-kind tie by choosing the single Pantry candidate, but a label
    photo overwrites an existing Food only when the printed identity names
    exactly one Food. Two Foods that share the printed name stay ambiguous
    whichever one is in the Pantry, and an ambiguous label creates a new Food.

    `label` is a LabelIdentity or the same fields as a mapping. `table` is the
    shared alias table from parse_alias_table(). `foods` are the existing Food
    nodes as frontmatter mappings, each with `name` and optionally `label_name`,
    `brand` and `barcode`; an entry whose `type` is not `food` is ignored.

    Stages, first hit wins:
    1. `barcode`: exactly one Food carries the same barcode. The package is
       that Food.
    2. `label`: the label name against the Foods alone, with the same exact ->
       alias -> fuzzy semantics as resolve_name(); the forms of a Food are its
       canonical name, its aliases and its `label_name`. Meals never take part,
       so a Meal never blocks the Food the package names. The first matching
       stage keeps every Food it found, and the printed brand then filters
       them: the printed brand and the brand the Food carries must agree both
       ways, so a Food of another brand, a generic Food that carries no brand
       and a Food that was not handed over in `foods` are all a different
       product, and a label that prints no brand keeps only a Food that carries
       no brand (a Food that was not handed over is the one exception: nothing
       disagrees, so it stays). Exactly one Food left is the package, and it is
       reused; zero or several left fall through to `new`.
    3. `new`: the canonical name to create. It is the label name, and it ends
       with the printed brand (spec #22: a packaged product ends with the
       brand), so a packaged name never takes the generic base name. The name
       is free of every existing Food and Meal name; a last resort adds a
       count. `candidates` holds the existing names that hold the base name.

    Only an existing Food is ever named, so a new label never overwrites a Meal.
    """
    label_name, brand, barcode = _label_fields(label)
    food_records = [
        dict(food) for food in foods
        if str(food.get("type", "food")) == "food" and str(food.get("name") or "")
    ]

    if barcode:
        same_barcode = sorted({str(f["name"]) for f in food_records if _clean(f.get("barcode")) == barcode})
        if len(same_barcode) == 1:
            return Resolution("barcode", same_barcode[0], tuple(same_barcode), "food")

    brands = {str(f["name"]): normalize_alias(str(f.get("brand") or "")) for f in food_records}
    printed = normalize_alias(brand or "")

    def same_brand(name: str) -> bool:
        """The brand the label prints and the brand the Food carries agree.

        The agreement holds both ways, because the brand is part of the product:
        a printed brand accepts only the same brand, so a Food of another brand
        and a generic Food with no brand are a different product; and a label
        that prints no brand accepts only a Food that carries no brand, because
        the package never names the brand the Food claims. The fuzzy stage
        matches a substring, so without this second half a generic `Milk` label
        would overwrite `Soy milk Alpro` with no question asked.

        A Food that was not handed over in `foods` has no brand to compare. It
        cannot confirm a printed brand, so a printed brand rejects it; a label
        with no brand still accepts it, because nothing disagrees.
        """
        carried = brands.get(name)
        if carried is None:
            return not printed
        return carried == printed

    if normalize_alias(label_name):
        _stage, hits = _stage_candidates(label_name, _food_table(table, food_records))
        kept = sorted({name for name, _kind in hits if same_brand(name)})
        if len(kept) == 1:
            return Resolution("label", kept[0], (kept[0],), "food")

    base = label_name.strip() or (brand or "").strip() or "New food"
    taken = _taken_forms(table, food_records)
    blocked = tuple(sorted(taken.get(normalize_alias(base), set())))
    return Resolution("new", _free_name(base, brand, taken), blocked, "food")


def _food_table(
    table: list[tuple[str, str, list[str]]],
    food_records: list[dict],
) -> list[tuple[str, str, list[str]]]:
    """The alias table of the Foods alone, for the label-name stages.

    Only the Index rows of kind `food` take part, so a Meal can never be a
    label candidate. Each Food's `label_name` joins its aliases when no form of
    that Food already normalizes to it, and a Food that is handed over in
    `foods` but is missing from the Index still takes part.
    """
    rows: dict[str, list[str]] = {}
    for name, kind, aliases in table:
        if kind == "food":
            rows.setdefault(name, []).extend(aliases)
    for food in food_records:
        name = str(food["name"])
        aliases = rows.setdefault(name, [])
        label_name = food.get("label_name")
        if label_name:
            forms = {normalize_alias(form) for form in [name] + aliases}
            if normalize_alias(str(label_name)) not in forms:
                aliases.append(str(label_name))
    return [(name, "food", aliases) for name, aliases in rows.items()]


def _taken_forms(
    table: list[tuple[str, str, list[str]]],
    food_records: list[dict],
) -> dict[str, set[str]]:
    """Map each normalized form of every Food and Meal to the names that hold it.

    The forms of one node are its canonical name, its aliases and, for a Food
    node, its `label_name`. A new label name must be free of all of them, so
    both kinds take part here; the label-name stages use _food_table() instead.
    """
    forms: dict[str, set[str]] = {}
    for name, _kind, aliases in table:
        for form in [name] + list(aliases):
            forms.setdefault(normalize_alias(form), set()).add(name)
    for food in food_records:
        for form in (food["name"], food.get("label_name")):
            if form:
                forms.setdefault(normalize_alias(str(form)), set()).add(str(food["name"]))
    return forms


def _label_fields(label: LabelIdentity | Mapping[str, str | None]) -> tuple[str, str | None, str | None]:
    """A LabelIdentity or the same fields as a mapping -> (label name, brand, barcode)."""
    if isinstance(label, LabelIdentity):
        return label.label_name or "", _clean(label.brand), _clean(label.barcode)
    return str(label.get("label_name") or ""), _clean(label.get("brand")), _clean(label.get("barcode"))


def _clean(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _free_name(base: str, brand: str | None, taken: Mapping[str, set[str]]) -> str:
    """The canonical name to create, always free.

    Spec #22: "a packaged product ends with the brand", so a printed brand goes
    last whether or not the base name is taken; it is not added twice when the
    label name already ends with it. A last resort adds a count, because the
    returned name must be free of every existing Food and Meal name.
    """
    stem = base
    if brand and not normalize_alias(stem).endswith(normalize_alias(brand)):
        stem = f"{base} {brand}"
    if normalize_alias(stem) not in taken:
        return stem
    count = 2
    while normalize_alias(f"{stem} {count}") in taken:
        count += 1
    return f"{stem} {count}"


# --------------------------------------------------------------------------
# pantry routine as functions
# --------------------------------------------------------------------------

def parse_pantry_item(text: str) -> tuple[str, str | None, str | None]:
    """`[[Name]] = <amount>, until <date>` -> (name, amount or None, until or None)."""
    match = PANTRY_ITEM_RE.match(text)
    if not match:
        raise ValueError(f"not a Pantry item string: {text!r}")
    return match.group(1), match.group(2), match.group(3)


def format_pantry_item(name: str, amount: str | None, until: str | None) -> str:
    text = f"[[{name}]]"
    if amount:
        text += f" = {amount}"
    if until:
        text += f", until {until}"
    return text


def _add_amounts(old: str | None, new: str | None) -> str | None:
    """Sum two amounts with the same unit; else the stated one wins."""
    if old and new:
        old_num, _, old_unit = old.partition(" ")
        new_num, _, new_unit = new.partition(" ")
        if old_unit == new_unit and is_number(old_num) and is_number(new_num):
            total = round_food_value(float(old_num) + float(new_num))
            return f"{total} {old_unit}"
    return new or old


def apply_pantry_change(data: dict, change: tuple, today: str) -> dict:
    """One chat change to the Pantry frontmatter. Returns a new dict.

    change is one of:
      ("bought", name, amount, until)  add an item; an existing item gets the amounts added;
                                       a staple is left alone
      ("gone", name)                   remove from whichever list holds it
      ("staple", name)                 make it a staple (moved out of items)
      ("item", name, amount, until)    make it an item (moved out of staples)
    Always sets `updated` to today.
    """
    result = dict(data)
    staples = list(data.get("staples") or [])
    items = list(data.get("items") or [])
    kind, name = change[0], change[1]
    link = f"[[{name}]]"
    index = next((i for i, item in enumerate(items) if parse_pantry_item(item)[0] == name), None)
    if kind == "bought":
        if link not in staples:
            _append_or_add(items, index, name, change[2], change[3])
    elif kind == "gone":
        staples = [s for s in staples if s != link]
        if index is not None:
            del items[index]
    elif kind == "staple":
        if index is not None:
            del items[index]
        if link not in staples:
            staples.append(link)
    elif kind == "item":
        staples = [s for s in staples if s != link]
        _append_or_add(items, index, name, change[2], change[3])
    else:
        raise ValueError(f"unknown Pantry change {kind!r}")
    result["staples"] = staples
    result["items"] = items
    result["updated"] = today
    return result


def _append_or_add(items: list[str], index: int | None, name: str, amount: str | None, until: str | None) -> None:
    """Append a new item, or add the amount to the existing item at `index`; a stated `until` replaces the old one."""
    if index is None:
        items.append(format_pantry_item(name, amount, until))
    else:
        _n, old_amount, old_until = parse_pantry_item(items[index])
        items[index] = format_pantry_item(name, _add_amounts(old_amount, amount), until or old_until)


def apply_restock(data: dict, additions: list[tuple[str, str | None, str | None]], today: str) -> tuple[dict, list[str]]:
    """Restock after the user's ok: every addition is a "bought" change; staples are skipped with a note."""
    notes = []
    result = dict(data)
    staples = set(data.get("staples") or [])
    for name, amount, until in additions:
        if f"[[{name}]]" in staples:
            notes.append(f"{name} is a staple, not added")
            continue
        result = apply_pantry_change(result, ("bought", name, amount, until), today)
    result["updated"] = today
    return result, notes


# --------------------------------------------------------------------------
# create-meal routine as functions
# --------------------------------------------------------------------------

def round_total(value: float) -> int:
    """Rounding rule for kcal, protein, fat and carbs on an entry line and in
    the totals of a Meal or Day: nearest whole number, a half rounds up.

    Fiber, sugar and salt keep one decimal with round_food_value(). Stated for
    the agent in routines/log.md step 4; the lint compares a stored value
    against the rounded one exactly, so an unrounded neighbour fails. The same
    arithmetic as round_bound(); the two rules are stated in two routines
    because they round two different things.
    """
    return _half_up(value)


def rounded_total(exact: float, decimals: int = 0) -> float:
    """`exact` as it must be stored: a whole number, or one decimal when `decimals` is 1."""
    return round_food_value(exact) if decimals else round_total(exact)


def matches_rounding(stored: float, exact: float, decimals: int = 0) -> bool:
    """`stored` is exactly `exact` rounded by the rule; a value the agent left
    unrounded, or rounded the other way at a half, fails."""
    return float(stored) == float(rounded_total(exact, decimals))


def round_totals(exact: Mapping[str, float]) -> dict:
    """The seven totals as stored: whole numbers for the four macros, one decimal for the nutrients."""
    return {
        **{key: round_total(exact[key]) for key in MACROS},
        **{key: round_food_value(exact[key]) for key in NUTRIENTS},
    }


def food_per_100g(food: Mapping[str, object]) -> dict:
    """The seven totals per 100 g of a Food. A missing nutrient counts as 0."""
    return {key: float(food.get(f"{key}_per_100g") or 0) for key in TOTALS}


def scale_food(food: Mapping[str, object], grams: float) -> dict:
    """The seven totals of `grams` of a Food, exact."""
    return {key: value * grams / 100 for key, value in food_per_100g(food).items()}


def parse_ingredient(text: str) -> tuple[str, float]:
    """`[[Food]] = <grams> g` -> (name, grams)."""
    match = INGREDIENT_RE.match(text)
    if not match:
        raise ValueError(f"not an ingredient string: {text!r}")
    return match.group(1), float(match.group(2))


@dataclass
class Totals:
    """The exact seven totals of a Meal or of one Day entry, its grams, and whether a node behind it is an estimate."""
    exact: dict
    weight_g: float
    estimated: bool


def compute_meal(ingredients: Iterable[str], foods: Mapping[str, Mapping[str, object]]) -> Totals:
    """routines/create-meal.md step 4: sum the ingredients over the Food nodes.

    Exact totals, the raw weight, and `estimated` true exactly when an
    ingredient Food has `number_source: estimate`. KeyError names an
    ingredient with no Food.
    """
    exact = {key: 0.0 for key in TOTALS}
    weight = 0.0
    estimated = False
    for item in ingredients:
        name, grams = parse_ingredient(item)
        food = foods[name]
        for key, value in scale_food(food, grams).items():
            exact[key] += value
        weight += grams
        estimated = estimated or food.get("number_source") == "estimate"
    return Totals(exact, weight, estimated)


def build_meal(name: str, ingredients: list[str], foods: Mapping[str, Mapping[str, object]], today: str,
               portions: int = 1, slots: Iterable[str] = (), aliases: Iterable[str] = (), reviewed: bool = False) -> dict:
    """routines/create-meal.md steps 4 and 5: the Meal frontmatter, before the ok (`reviewed: false`) or after it."""
    totals = compute_meal(ingredients, foods)
    aliases, slots = list(aliases), list(slots)
    data: dict = {"type": "meal", "name": name}
    if aliases:
        data["aliases"] = aliases
    if slots:
        data["slots"] = slots
    data["ingredients"] = list(ingredients)
    data["portions"] = portions
    data["weight_g"] = round_food_value(totals.weight_g)
    data.update(round_totals(totals.exact))
    data["totals_date"] = today
    data["estimated"] = "true" if totals.estimated else "false"
    data["reviewed"] = "true" if reviewed else "false"
    return data


def meal_index_line(data: Mapping[str, object]) -> str:
    """routines/create-meal.md Write: `- [[Name]] | <slots or any> | <aliases>`, the Meal line of the shared alias table."""
    slots = data.get("slots") or []
    line = f"- [[{data['name']}]] | {', '.join(slots) if slots else 'any'}"
    aliases = data.get("aliases") or []
    if aliases:
        line += f" | {', '.join(aliases)}"
    return line


# --------------------------------------------------------------------------
# log routine as functions
# --------------------------------------------------------------------------

@dataclass
class Entry:
    """One entry line of a Day, parsed or about to be written.

    `unit` is `g` or `portion`. `marked` is the `~` right after the bullet.
    `change` is the ingredient change `(Food, grams)` or None. `macros` holds
    the four whole numbers on the line: kcal, protein_g, fat_g, carbs_g.
    """
    name: str
    amount: float
    unit: str
    macros: dict
    marked: bool = False
    change: tuple[str, float] | None = None


def parse_entry_line(line: str) -> Entry:
    """The canonical entry line of routines/log.md step 5 -> Entry. ValueError when the shape is off."""
    match = ENTRY_LINE_RE.match(line)
    if not match:
        raise ValueError(f"not an entry line: {line!r}")
    mark, name, amount, unit, change_name, change_grams, kcal, protein, fat, carbs = match.groups()
    change = (change_name, float(change_grams)) if change_name else None
    macros = {"kcal": int(kcal), "protein_g": int(protein), "fat_g": int(fat), "carbs_g": int(carbs)}
    return Entry(name, float(amount), unit, macros, mark is not None, change)


def format_entry_line(entry: Entry) -> str:
    """Entry -> the canonical line of routines/log.md steps 5 and 6: `- ~ [[Name]] = <n> g — <kcal> kcal · <P> P · <F> F · <C> C`."""
    text = "- ~ " if entry.marked else "- "
    text += f"[[{entry.name}]] = {_num(entry.amount)} {entry.unit}"
    if entry.change:
        text += f", [[{entry.change[0]}]] = {_num(entry.change[1])} g"
    m = entry.macros
    return text + f" — {m['kcal']} kcal · {m['protein_g']} P · {m['fat_g']} F · {m['carbs_g']} C"


def _num(value: float) -> str:
    return str(int(value)) if float(value) == int(value) else str(value)


def entry_totals(node: Mapping[str, object], amount: float, unit: str,
                 foods: Mapping[str, Mapping[str, object]] | None = None, change: tuple[str, float] | None = None) -> Totals:
    """routines/log.md steps 4 and 5: the exact seven totals of one entry from its node, and whether the node is an estimate.

    A Food: per 100 g times the grams; `unit` must be `g`. A Meal: its stored
    totals times portions / `portions`, or times grams / `weight_g`. An
    ingredient change, Meal by portion only: the eaten portions of the stored
    totals, minus the eaten portions of the ingredient as the Meal lists it,
    plus the amount eaten. So "usual breakfast with 300 g skyr" means 300 g
    of skyr on the plate whatever the Meal's portion count. The node-side
    estimate is `number_source: estimate` on a Food or `estimated: true` on a
    Meal; a guessed amount is the caller's flag. ValueError names a shape the
    routine forbids.
    """
    if node.get("type") == "food":
        if unit != "g":
            raise ValueError(f"[[{node.get('name')}]] is a Food and is logged in grams, not `{unit}`")
        if change:
            raise ValueError(f"an ingredient change needs a Meal, [[{node.get('name')}]] is a Food")
        return Totals(scale_food(node, amount), amount, node.get("number_source") == "estimate")
    factor = amount / float(node["portions"]) if unit == "portion" else amount / float(node["weight_g"])
    exact = {key: float(node.get(key) or 0) * factor for key in TOTALS}
    if change:
        if unit != "portion":
            raise ValueError(f"an ingredient change is logged by portion, not `{unit}`")
        food_name, grams = change
        listed = dict(parse_ingredient(item) for item in node.get("ingredients") or [])
        if food_name not in listed:
            raise ValueError(f"ingredient change names [[{food_name}]], which is not an ingredient of [[{node.get('name')}]]")
        food = (foods or {})[food_name]
        for key in TOTALS:
            exact[key] += scale_food(food, grams)[key] - scale_food(food, listed[food_name])[key] * factor
    return Totals(exact, amount, node.get("estimated") == "true")


def log_entry(node: Mapping[str, object], amount: float, unit: str, guessed: bool = False,
              foods: Mapping[str, Mapping[str, object]] | None = None, change: tuple[str, float] | None = None) -> Entry:
    """routines/log.md steps 4 to 6: the Entry to write, macros by the rounding rule, the mark when the node or the amount is estimated."""
    totals = entry_totals(node, amount, unit, foods, change)
    macros = {key: round_total(totals.exact[key]) for key in MACROS}
    return Entry(str(node["name"]), amount, unit, macros, totals.estimated or guessed, change)


def day_totals(entries: Iterable[Entry], exact_nutrients: Iterable[Mapping[str, float]] = ()) -> dict:
    """routines/log.md step 7: the seven Day totals and `estimated`.

    The four macros are the sum of the line numbers. Fiber, sugar and salt
    are the exact sum over the entries' Totals, rounded once to one decimal.
    """
    entries = list(entries)
    result: dict = {key: sum(e.macros[key] for e in entries) for key in MACROS}
    nutrients = list(exact_nutrients)
    for key in NUTRIENTS:
        result[key] = round_food_value(sum(n[key] for n in nutrients))
    result["estimated"] = "true" if any(e.marked for e in entries) else "false"
    return result


def pick_slot(word: str | None, clock: str | None, filled: Iterable[str] = ()) -> str:
    """routines/log.md step 3, the slot rule: the user's word, else the clock, else the next slot in order.

    Clock: before 11:00 breakfast, 11:00 to 15:00 lunch, 15:00 to 18:00 snack,
    after 18:00 dinner. When the clock slot already holds an entry from an
    earlier message (`filled`), the next slot in order that is not filled;
    after dinner there is no next slot, so dinner takes it.
    """
    if word:
        if word.lower() not in SLOTS:
            raise ValueError(f"{word!r} is not a slot word")
        return word.lower()
    if clock is None:
        raise ValueError("a slot needs the user's word or the clock")
    hour, _, minute = clock.partition(":")
    minutes = int(hour) * 60 + int(minute or 0)
    if minutes < 11 * 60:
        slot = "breakfast"
    elif minutes < 15 * 60:
        slot = "lunch"
    elif minutes < 18 * 60:
        slot = "snack"
    else:
        slot = "dinner"
    filled_set = set(filled)
    for candidate in SLOTS[SLOTS.index(slot):]:
        if candidate not in filled_set:
            return candidate
    return "dinner"


# --------------------------------------------------------------------------
# rebalance routine as functions
# --------------------------------------------------------------------------

def remaining(goals: Mapping[str, object], day: Mapping[str, object]) -> dict:
    """routines/rebalance.md step 1: remaining = target minus running totals, for kcal, protein, fat, carbs."""
    return {key: round_total(float(goals[key]) - float(day.get(key) or 0)) for key in MACROS}


def over_max(goals: Mapping[str, object], day: Mapping[str, object]) -> list[str]:
    """routines/rebalance.md step 1: the macros whose running total is above the stored max."""
    return [key for key in MACROS if float(day.get(key) or 0) > float(goals[f"{key}_max"])]


def open_slots(filled: Iterable[str], removed: Iterable[str] = ()) -> list[str]:
    """routines/rebalance.md step 2: slots with no entry, in the fixed order, minus the slots removed in chat."""
    taken = set(filled) | set(removed)
    return [slot for slot in SLOTS if slot not in taken]


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


class LintFailure(Exception):
    """Raised on the first violation. The lint stops there."""


@dataclass
class Vault:
    root: Path
    nodes: list[Node] = field(default_factory=list)

    def fail(self, rel: str, message: str) -> None:
        raise LintFailure(f"{rel}: {message}")

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


def check_node_locations(vault: Vault) -> None:
    """A node file lives under nodes/. Node frontmatter anywhere else is a stray node.

    load_nodes() reads nodes/ only, so a file with `type: food` at the vault
    root would otherwise pass unseen. Hidden folders (.git, .obsidian and the
    like) are not part of the vault and are skipped.
    """
    for path in sorted(vault.root.rglob("*.md")):
        rel = path.relative_to(vault.root).as_posix()
        if rel.startswith("nodes/") or any(part.startswith(".") for part in rel.split("/")):
            continue
        try:
            data, _body = parse_frontmatter(path.read_text(encoding="utf-8"))
        except FrontmatterError:
            continue
        node_type = data.get("type")
        if node_type in NODE_TYPES:
            vault.fail(rel, f"a {node_type} node must live under nodes/, not at {rel}")


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
        targets = {m: float(data[m]) for m in MACROS if is_number(data.get(m, ""))}
        if len(targets) == len(MACROS):
            expected = compute_bounds(targets, float(data["tolerance_pct"]))
            for key, want in expected.items():
                if key not in data:
                    vault.fail(node.rel, f"missing `{key}`")
                elif not is_number(data[key]) or float(data[key]) != want:
                    vault.fail(node.rel, f"`{key}` is {data[key]!r}, expected {want} by the rounding rule in routines/goals.md")
        allowed = set(MACROS) | {"type", "name", "tolerance_pct", "since"} | {f"{m}_{b}" for m in MACROS for b in ("min", "max")}
        for key in data:
            if key not in allowed:
                vault.fail(node.rel, f"unexpected property `{key}` on Goals")


def _check_enum(vault: Vault, node: Node, key: str, allowed: tuple) -> None:
    value = node.data.get(key)
    if value not in allowed:
        vault.fail(node.rel, f"`{key}` {value!r} is not one of {', '.join(allowed)}")


def _check_body_notes_only(vault: Vault, node: Node) -> None:
    """The body is empty, or one `## Notes` section and nothing else."""
    _check_body_sections(vault, node, ("Notes",))


def _check_body_sections(vault: Vault, node: Node, allowed: tuple[str, ...]) -> list[str]:
    """The body holds only the `##` sections in `allowed`, each at most once, in that order.

    `_sections()` drops the lines before the first heading, so it cannot see
    free prose. This walks every body line instead: no other heading at any
    level, no second copy of a heading, no heading out of order, and no text
    before the first heading. Returns the headings found, in order.
    """
    what = " and ".join(f"`## {name}`" for name in allowed)
    plural = "sections" if len(allowed) > 1 else "section"
    seen: list[str] = []
    in_fence = False
    for line in node.body.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            if not seen:
                vault.fail(node.rel, f"body may hold only the optional {what} {plural}, found text before the first heading")
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match:
            heading = f"{match.group(1)} {match.group(2).strip()}"
            name = match.group(2).strip()
            if match.group(1) != "##" or name not in allowed:
                vault.fail(node.rel, f"body may hold only the optional {what} {plural}, found heading `{heading}`")
            if name in seen:
                vault.fail(node.rel, f"body has a second `## {name}` heading; one is the maximum")
            if seen and allowed.index(name) < allowed.index(seen[-1]):
                vault.fail(node.rel, f"body sections must follow the order {what}; `## {name}` comes after `## {seen[-1]}`")
            seen.append(name)
            continue
        if not seen and line.strip():
            vault.fail(node.rel, f"body may hold only the optional {what} {plural}, found text outside it: {line.strip()!r}")
    return seen


def _check_wikilink_property(vault: Vault, node: Node, key: str, allowed_types: tuple) -> None:
    value = node.data.get(key)
    match = QUOTED_LINK_RE.match(value) if isinstance(value, str) else None
    if not match:
        vault.fail(node.rel, f"`{key}` must be a quoted wikilink like \"[[Name]]\", got {value!r}")
        return
    target = vault.node_by_name(match.group(1))
    if target is None:
        vault.fail(node.rel, f"`{key}` points to [[{match.group(1)}]], which does not exist")
    elif target.type not in allowed_types:
        vault.fail(node.rel, f"`{key}` points to [[{match.group(1)}]], a {target.type} node, not {' or '.join(allowed_types)}")


def check_foods(vault: Vault) -> None:
    for node in vault.nodes:
        if node.type != "food":
            continue
        data = node.data
        if node.rel != f"nodes/food/{node.base_name}.md":
            vault.fail(node.rel, f"a Food must sit directly at nodes/food/{node.base_name}.md")
        for key in FOOD_REQUIRED:
            if key not in data:
                vault.fail(node.rel, f"missing `{key}`")
        for key in FOOD_MACROS + FOOD_OPTIONAL_NUMBERS:
            if key in data and not is_number(data[key]):
                vault.fail(node.rel, f"`{key}` must be a number, got {data[key]!r}")
        for key in FOOD_MACROS + FOOD_NUTRIENTS:
            if key in data and float(data[key]) != round_food_value(float(data[key])):
                vault.fail(node.rel, f"`{key}` is {data[key]!r}, expected {round_food_value(float(data[key]))} by the rounding rule in routines/create-food.md")
        _check_enum(vault, node, "category", FOOD_CATEGORIES)
        _check_enum(vault, node, "label_basis", LABEL_BASES)
        _check_enum(vault, node, "number_source", NUMBER_SOURCES)
        _check_enum(vault, node, "reviewed", CHECKBOX_VALUES)
        if not is_date(data["source_date"]):
            vault.fail(node.rel, f"`source_date` must be a date YYYY-MM-DD, got {data['source_date']!r}")
        for key in data:
            if key not in FOOD_REQUIRED + FOOD_OPTIONAL:
                vault.fail(node.rel, f"unexpected property `{key}` on a Food")
        for key in ("aliases", "servings"):
            if key in data and not isinstance(data[key], list):
                vault.fail(node.rel, f"`{key}` must be a list")
        if "label_name" in data:
            aliases = data.get("aliases")
            if not isinstance(aliases, list) or data["label_name"] not in aliases:
                vault.fail(node.rel, f"`label_name` {data['label_name']!r} must also be an item of `aliases`")
        for serving in data.get("servings", []):
            if not SERVING_RE.match(serving):
                vault.fail(node.rel, f"`servings` item must be `<count> <unit> = <grams> g`, got {serving!r}")
        if data["label_basis"] == "100ml" and "density_g_per_ml" not in data:
            vault.fail(node.rel, "`label_basis: 100ml` needs `density_g_per_ml` (and `density_source`)")
        if "density_g_per_ml" in data and "density_source" not in data:
            vault.fail(node.rel, "`density_g_per_ml` needs `density_source`")
        if "density_source" in data:
            if "density_g_per_ml" not in data:
                vault.fail(node.rel, "`density_source` is present without `density_g_per_ml`")
            _check_enum(vault, node, "density_source", NUMBER_SOURCES)
        if data.get("number_source") == "estimate" and "estimated_from" not in data:
            vault.fail(node.rel, "`number_source: estimate` needs `estimated_from` as a quoted wikilink to the Food the estimate came from")
        if "estimated_from" in data:
            _check_wikilink_property(vault, node, "estimated_from", ("food",))
        _check_body_notes_only(vault, node)


def check_pantry(vault: Vault) -> None:
    pantries = [n for n in vault.nodes if n.type == "pantry"]
    if not pantries:
        vault.fail("nodes/pantry/Pantry.md", "the vault needs exactly one Pantry node and this file is missing")
    if len(pantries) > 1:
        vault.fail(pantries[1].rel, "more than one Pantry node")
    for node in pantries:
        data = node.data
        if node.rel != "nodes/pantry/Pantry.md":
            vault.fail(node.rel, "Pantry node must be nodes/pantry/Pantry.md")
        for key in PANTRY_REQUIRED:
            if key not in data:
                vault.fail(node.rel, f"missing `{key}`")
        if not is_date(data["updated"]):
            vault.fail(node.rel, f"`updated` must be a date YYYY-MM-DD, got {data['updated']!r}")
        for key in data:
            if key not in PANTRY_REQUIRED + PANTRY_OPTIONAL:
                vault.fail(node.rel, f"unexpected property `{key}` on the Pantry")
        for key in PANTRY_OPTIONAL:
            if key in data and not isinstance(data[key], list):
                vault.fail(node.rel, f"`{key}` must be a list")
        seen: set[str] = set()
        for staple in data.get("staples", []):
            match = QUOTED_LINK_RE.match(staple)
            if not match:
                vault.fail(node.rel, f"`staples` item must be `[[Food]]` only, got {staple!r}")
                continue
            target = vault.node_by_name(match.group(1))
            if target is None:
                vault.fail(node.rel, f"`staples` links to [[{match.group(1)}]], which does not exist")
            elif target.type != "food":
                vault.fail(node.rel, f"`staples` links to [[{match.group(1)}]], a {target.type} node, not a Food")
            _seen_once(vault, node, seen, match.group(1))
        for item in data.get("items", []):
            match = PANTRY_ITEM_RE.match(item)
            if not match:
                vault.fail(node.rel, f"`items` item must be `[[Name]]`, `= <amount>` and `, until <date>` optional, got {item!r}")
                continue
            name, amount, _until = match.groups()
            target = vault.node_by_name(name)
            if target is None:
                vault.fail(node.rel, f"`items` links to [[{name}]], which does not exist")
            elif target.type not in ("food", "meal"):
                vault.fail(node.rel, f"`items` links to [[{name}]], a {target.type} node, not a Food or Meal")
            elif amount is not None:
                shape = FOOD_AMOUNT_RE if target.type == "food" else MEAL_AMOUNT_RE
                if not shape.match(amount):
                    want = "`<n> g`" if target.type == "food" else "`<n> portion` or `<n> g cooked`"
                    vault.fail(node.rel, f"`items` amount for [[{name}]] must be {want}, got {amount!r}")
            _seen_once(vault, node, seen, name)
        _check_body_notes_only(vault, node)


def _seen_once(vault: Vault, node: Node, seen: set[str], name: str) -> None:
    if name in seen:
        vault.fail(node.rel, f"[[{name}]] is listed twice in the Pantry")
    seen.add(name)


def _check_number(vault: Vault, node: Node, key: str) -> None:
    if key in node.data and not is_number(node.data[key]):
        vault.fail(node.rel, f"`{key}` must be a number, got {node.data[key]!r}")


def _check_list(vault: Vault, node: Node, key: str) -> None:
    if key in node.data and not isinstance(node.data[key], list):
        vault.fail(node.rel, f"`{key}` must be a list")


def _check_slots(vault: Vault, node: Node) -> None:
    """`slots` is a list of distinct slot words; absent means any slot."""
    _check_list(vault, node, "slots")
    seen: set[str] = set()
    for slot in node.data.get("slots", []):
        if slot not in SLOTS:
            vault.fail(node.rel, f"`slots` item {slot!r} is not one of {', '.join(SLOTS)}")
        if slot in seen:
            vault.fail(node.rel, f"`slots` lists {slot!r} twice")
        seen.add(slot)


def check_meals(vault: Vault) -> None:
    foods = {n.base_name: n.data for n in vault.nodes if n.type == "food"}
    for node in vault.nodes:
        if node.type != "meal":
            continue
        data = node.data
        if node.rel != f"nodes/meal/{node.base_name}.md":
            vault.fail(node.rel, f"a Meal must sit directly at nodes/meal/{node.base_name}.md")
        for key in MEAL_REQUIRED:
            if key not in data:
                vault.fail(node.rel, f"missing `{key}`")
        for key in data:
            if key not in MEAL_REQUIRED + MEAL_OPTIONAL:
                vault.fail(node.rel, f"unexpected property `{key}` on a Meal")
        for key in ("portions", "weight_g", "cooked_weight_g") + TOTALS:
            _check_number(vault, node, key)
        if float(data["portions"]) <= 0:
            vault.fail(node.rel, f"`portions` must be above 0, got {data['portions']!r}")
        if not is_date(data["totals_date"]):
            vault.fail(node.rel, f"`totals_date` must be a date YYYY-MM-DD, got {data['totals_date']!r}")
        _check_enum(vault, node, "estimated", CHECKBOX_VALUES)
        _check_enum(vault, node, "reviewed", CHECKBOX_VALUES)
        _check_list(vault, node, "aliases")
        _check_slots(vault, node)
        _check_list(vault, node, "ingredients")
        if not data["ingredients"]:
            vault.fail(node.rel, "`ingredients` must hold at least one `[[Food]] = <grams> g` item")
        seen: set[str] = set()
        for item in data["ingredients"]:
            match = INGREDIENT_RE.match(item)
            if not match:
                vault.fail(node.rel, f"`ingredients` item must be `[[Food]] = <grams> g`, got {item!r}")
            name = match.group(1)
            target = vault.node_by_name(name)
            if target is None:
                vault.fail(node.rel, f"`ingredients` links to [[{name}]], which does not exist")
            elif target.type != "food":
                vault.fail(node.rel, f"`ingredients` links to [[{name}]], a {target.type} node, not a Food; a Meal never contains a Meal")
            if name in seen:
                vault.fail(node.rel, f"`ingredients` lists [[{name}]] twice; one item per Food")
            seen.add(name)
            for key in NUTRIENTS:
                if f"{key}_per_100g" not in target.data:
                    vault.fail(node.rel, f"ingredient [[{name}]] has no `{key}_per_100g`; fill it on the Food before the Meal sums it")
        totals = compute_meal(data["ingredients"], foods)
        if abs(float(data["weight_g"]) - totals.weight_g) > 1e-6:
            vault.fail(node.rel, f"`weight_g` is {data['weight_g']!r}, the ingredients sum to {_num(totals.weight_g)}")
        for key in TOTALS:
            decimals = 1 if key in NUTRIENTS else 0
            if not matches_rounding(data[key], totals.exact[key], decimals):
                want = rounded_total(totals.exact[key], decimals)
                vault.fail(node.rel, f"`{key}` is {data[key]!r}, the Food nodes give {want} by the rounding rule in routines/log.md")
        want_estimated = "true" if totals.estimated else "false"
        if data["estimated"] != want_estimated:
            reason = "an ingredient Food is an estimate" if totals.estimated else "no ingredient Food is an estimate"
            vault.fail(node.rel, f"`estimated` is {data['estimated']!r} but {reason}; it must be {want_estimated}")
        _check_body_sections(vault, node, MEAL_BODY_SECTIONS)


def check_days(vault: Vault) -> None:
    """Every Day: location by date, schema, slot order, entry lines, totals from the lines, the mark.

    The four macros in the frontmatter equal the sum of the lines on every
    Day. An open Day is the one being written now, so its lines and its three
    nutrient totals must also match the nodes within the rounding rule. A
    closed or auto-closed Day keeps its totals when a Food changes later.
    """
    foods = {n.base_name: n.data for n in vault.nodes if n.type == "food"}
    for node in vault.nodes:
        if node.type != "day":
            continue
        data = node.data
        for key in DAY_REQUIRED:
            if key not in data:
                vault.fail(node.rel, f"missing `{key}`")
        for key in data:
            if key not in DAY_REQUIRED:
                vault.fail(node.rel, f"unexpected property `{key}` on a Day")
        if not is_date(data["date"]):
            vault.fail(node.rel, f"`date` must be a date YYYY-MM-DD, got {data['date']!r}")
        if data["date"] != node.base_name:
            vault.fail(node.rel, f"`date` {data['date']!r} differs from the file name {node.base_name!r}")
        if node.rel != f"nodes/day/{data['date'][:7]}/{data['date']}.md":
            vault.fail(node.rel, f"a Day must sit at nodes/day/{data['date'][:7]}/{data['date']}.md, its month folder")
        _check_enum(vault, node, "status", DAY_STATUSES)
        _check_wikilink_property(vault, node, "goal", ("goals",))
        for key in TOTALS:
            _check_number(vault, node, key)
        _check_enum(vault, node, "estimated", CHECKBOX_VALUES)
        headings = _check_body_sections(vault, node, DAY_BODY_SECTIONS)
        sections = _sections(node.body)
        entries: list[Entry] = []
        exact_totals: list[dict] = []
        for heading in headings:
            if heading not in SLOT_HEADINGS:
                continue
            lines = [line for line in sections[heading] if line.strip()]
            if not lines:
                vault.fail(node.rel, f"`## {heading}` has no entry; a slot section is present only when it has an entry")
            for line in lines:
                entry, exact = _check_entry_line(vault, node, heading, line, foods)
                entries.append(entry)
                exact_totals.append(exact)
        for key in MACROS:
            want = sum(e.macros[key] for e in entries)
            if float(data[key]) != want:
                vault.fail(node.rel, f"`{key}` is {data[key]!r}, the entry lines sum to {want}")
        want_estimated = "true" if any(e.marked for e in entries) else "false"
        if data["estimated"] != want_estimated:
            reason = "an entry line carries the `~` mark" if want_estimated == "true" else "no entry line carries the `~` mark"
            vault.fail(node.rel, f"`estimated` is {data['estimated']!r} but {reason}; it must be {want_estimated}")
        if data["status"] == "open":
            for key in NUTRIENTS:
                exact = sum(t[key] for t in exact_totals)
                if not matches_rounding(data[key], exact, 1):
                    vault.fail(node.rel, f"`{key}` is {data[key]!r}, the nodes give {round_food_value(exact)} for the entry lines")


def _check_entry_line(vault: Vault, node: Node, heading: str, line: str, foods: Mapping[str, Mapping[str, object]]) -> tuple[Entry, dict]:
    """One line under a slot heading: a canonical entry line whose links resolve, computable from its node, marked when the node is an estimate.

    Returns the Entry and its exact seven totals. The shape rules (a Food in
    grams, the ingredient change by portion on a Meal naming one of its
    ingredients) live in entry_totals(); its ValueError becomes the failure.
    On an open Day the line macros must match the node within the rounding.
    """
    try:
        entry = parse_entry_line(line)
    except ValueError:
        vault.fail(node.rel, f"`## {heading}` line is not a canonical entry line `- [[Name]] = <n> g — <kcal> kcal · <P> P · <F> F · <C> C` (`- ~ ` marks an estimate): {line!r}")
    target = vault.node_by_name(entry.name)
    if target is None:
        vault.fail(node.rel, f"`## {heading}` links to [[{entry.name}]], which does not exist")
    elif target.type not in ("food", "meal"):
        vault.fail(node.rel, f"`## {heading}` links to [[{entry.name}]], a {target.type} node, not a Food or Meal")
    try:
        totals = entry_totals(target.data, entry.amount, entry.unit, foods, entry.change)
    except ValueError as exc:
        vault.fail(node.rel, f"{exc}: {line!r}")
    except (KeyError, TypeError, ZeroDivisionError) as exc:
        vault.fail(node.rel, f"cannot compute [[{entry.name}]] = {_num(entry.amount)} {entry.unit} from its node ({exc!r}): {line!r}")
    if totals.estimated and not entry.marked:
        what = "an estimated Food" if target.type == "food" else "an estimated Meal"
        vault.fail(node.rel, f"[[{entry.name}]] is {what}, so the line needs the `~` mark right after the bullet: {line!r}")
    if node.data.get("status") == "open":
        for key in MACROS:
            if not matches_rounding(entry.macros[key], totals.exact[key]):
                vault.fail(node.rel, f"[[{entry.name}]] = {_num(entry.amount)} {entry.unit} says {key} {entry.macros[key]}, the node gives {round_total(totals.exact[key])} by the rounding rule in routines/log.md")
    return entry, totals.exact


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
    if data.get("type") != "state":
        vault.fail("state.md", "`type` must be `state`")
    if "open_day" not in data:
        vault.fail("state.md", "missing `open_day`")
    if "updated" not in data:
        vault.fail("state.md", "missing `updated`")
    elif not is_date(data["updated"]):
        vault.fail("state.md", f"`updated` must be a date YYYY-MM-DD, got {data['updated']!r}")

    open_days = [n for n in vault.nodes if n.type == "day" and n.data.get("status") == "open"]
    if len(open_days) > 1:
        vault.fail(open_days[1].rel, f"a second Day with status open; only one Day is open at a time (also {open_days[0].rel})")
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
    months: set[str] = set()
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
                if month in months:
                    vault.fail("index.md", f"month {month} must have exactly one Day line, found a second: {line!r}")
                months.add(month)
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
            if name in indexed:
                vault.fail("index.md", f"[[{name}]] must have exactly one Index line, found a second: {line!r}")
            if section == "Food":
                _check_food_index_line(vault, node, line)
            if section == "Meal":
                _check_meal_index_line(vault, node, line)
            indexed.add(name)

    for node in vault.nodes:
        if node.type in ("food", "meal", "goals", "pantry") and node.base_name not in indexed:
            vault.fail("index.md", f"no line for [[{node.base_name}]] ({node.rel})")
    day_root = vault.root / "nodes" / "day"
    if day_root.is_dir():
        for folder in sorted(day_root.iterdir()):
            if folder.is_dir() and re.fullmatch(r"\d{4}-\d{2}", folder.name) and folder.name not in months:
                vault.fail("index.md", f"no Day month line for the folder nodes/day/{folder.name}/: `- {folder.name} | nodes/day/{folder.name}/`")


def _check_food_index_line(vault: Vault, node: Node, line: str) -> None:
    """`- [[Name]] | <category> | <aliases plus label name, comma separated>`."""
    fields = _index_fields(vault, node, line, "Food", "<category>")
    category = node.data.get("category")
    if fields[1] != category:
        vault.fail("index.md", f"[[{node.base_name}]] line says category {fields[1]!r}, the node says {category!r}")
    expected = _alias_set(node)
    if node.data.get("label_name"):
        expected.add(node.data["label_name"])
    _check_index_aliases(vault, node, fields, expected)


def _check_meal_index_line(vault: Vault, node: Node, line: str) -> None:
    """`- [[Name]] | <slots, comma separated, or any> | <aliases, comma separated>`."""
    fields = _index_fields(vault, node, line, "Meal", "<slots or any>")
    slots = node.data.get("slots") or []
    want = ", ".join(slots) if isinstance(slots, list) and slots else "any"
    if fields[1] != want:
        vault.fail("index.md", f"[[{node.base_name}]] line says slots {fields[1]!r}, the node says {want!r}")
    _check_index_aliases(vault, node, fields, _alias_set(node))


def _index_fields(vault: Vault, node: Node, line: str, kind: str, second: str) -> list[str]:
    fields = [f.strip() for f in line[2:].split(" | ")]
    if len(fields) < 2 or len(fields) > 3:
        vault.fail("index.md", f"{kind} line must be `- [[Name]] | {second} | <aliases>`: {line!r}")
    return fields


def _alias_set(node: Node) -> set[str]:
    aliases = node.data.get("aliases", [])
    return set(aliases if isinstance(aliases, list) else [])


def _check_index_aliases(vault: Vault, node: Node, fields: list[str], expected: set[str]) -> None:
    listed = {a.strip() for a in fields[2].split(",") if a.strip()} if len(fields) == 3 else set()
    missing = sorted(expected - listed)
    extra = sorted(listed - expected)
    if missing:
        vault.fail("index.md", f"[[{node.base_name}]] line lacks alias(es) {missing}")
    if extra:
        vault.fail("index.md", f"[[{node.base_name}]] line has alias(es) {extra} that the node does not")


def check_routines(vault: Vault) -> None:
    routines = vault.root / "routines"
    if not routines.is_dir():
        return
    for path in sorted(routines.glob("*.md")):
        rel = path.relative_to(vault.root).as_posix()
        text = path.read_text(encoding="utf-8")
        sections = _sections(text)
        for name in ROUTINE_SECTIONS:
            if name not in sections:
                vault.fail(rel, f"missing `## {name}` section")
        tokens = estimate_tokens(text)
        if tokens >= ROUTINE_TOKEN_LIMIT:
            vault.fail(rel, f"about {tokens} tokens, limit is under {ROUTINE_TOKEN_LIMIT} (estimate: characters / 4)")


def _sections(text: str) -> dict[str, list[str]]:
    """Split markdown into `## Heading` -> lines. Lines before the first heading are dropped; fenced code never opens a section."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if line.startswith("## ") and not in_fence:
            current = line[3:].strip()
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return sections


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

CHECKS = (
    load_nodes,
    check_common_conventions,
    check_node_locations,
    check_goals,
    check_foods,
    check_meals,
    check_days,
    check_pantry,
    check_router,
    check_state,
    check_index,
    check_routines,
)


def lint_vault(root: Path) -> list[str]:
    """Run the checks in order. Return [] when clean, else a one-item list with the first violation."""
    vault = Vault(Path(root))
    try:
        for check in CHECKS:
            check(vault)
    except LintFailure as exc:
        return [str(exc)]
    return []


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    errors = lint_vault(root)
    if errors:
        print(f"FAIL {errors[0]}")
        return 1
    print("vault lint: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
