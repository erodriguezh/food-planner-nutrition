# Spec: nodes

Schemas of the node files under `nodes/`. Derived from the spec issue
([#22](https://github.com/erodriguezh/food-planner-nutrition/issues/22)).
The agent never loads this document in daily use; the routines carry the method.
The vault lint (`python3 lint/vault_lint.py`) checks every node against these schemas.

## Common conventions

- Flat YAML frontmatter only. Core Obsidian types: text, list, number, checkbox, date. No nested objects, no flow collections.
- Every node has `type` and `name`. `name` equals the file base name. Base names are unique across the vault.
- `type` is one of `food`, `meal`, `day`, `goals`, `pantry`.
- Wikilinks inside properties are quoted strings, for example `goal: "[[Goals]]"`. Links use canonical names, never aliases.
- Amounts are grams. Column order everywhere is kcal, protein, fat, carbs.
- Dates are `YYYY-MM-DD`.

## Goals

One file: `nodes/goals/Goals.md`. Built by ticket
[#23](https://github.com/erodriguezh/food-planner-nutrition/issues/23);
written and rewritten only by `routines/goals.md`.

### Frontmatter

All properties are required. No other property is allowed: the spec forbids a history table, day types and fiber, sugar or salt targets.

| Property | Type | Meaning |
| --- | --- | --- |
| `type` | text | always `goals` |
| `name` | text | always `Goals` |
| `kcal` | number | daily calorie target |
| `protein_g` | number | daily protein target in grams |
| `fat_g` | number | daily fat target in grams |
| `carbs_g` | number | daily carbs target in grams |
| `tolerance_pct` | number | percent applied to every target to build its range; default 5 |
| `kcal_min`, `kcal_max` | number | stored range for kcal |
| `protein_g_min`, `protein_g_max` | number | stored range for protein |
| `fat_g_min`, `fat_g_max` | number | stored range for fat |
| `carbs_g_min`, `carbs_g_max` | number | stored range for carbs |
| `since` | date | the day the current values were written |

### Rules

- `<macro>_min` = `<macro>` × (1 − `tolerance_pct` / 100); `<macro>_max` = `<macro>` × (1 + `tolerance_pct` / 100).
- Bounds are stored as whole numbers. The rounding rule is stated in one place, `routines/goals.md` step 4, and the lint applies it in `round_bound()`.
- First setup: the user states the four targets; the agent asks once for any missing one. `tolerance_pct` is 5 when the user does not state one.
- Later change: the user states one or more targets, a tolerance, or both. Every target the user does not name keeps its stored value. A tolerance the user does not name keeps the stored `tolerance_pct`; the default 5 applies at first setup only. Example: with tolerance 10 stored, "set protein to 160" gives 2500 / 160 / 60 / 355, tolerance 10, and all eight bounds at 10 %.
- Every change, however small, rewrites all four targets, the tolerance, all eight bounds and `since`. Nothing is recomputed at read time. Git keeps the history.
- No history table, no day types, no fiber, sugar or salt targets.
- The Index holds one pointer line under `## Goals`: `- [[Goals]]`.
- Each closed Day Summary records the targets it used, so a goal change does not touch old Days.

### Body

Optional `## Notes` section only.

### Example

```
---
type: goals
name: Goals
kcal: 2500
protein_g: 135
fat_g: 60
carbs_g: 355
tolerance_pct: 5
kcal_min: 2375
kcal_max: 2625
protein_g_min: 128
protein_g_max: 142
fat_g_min: 57
fat_g_max: 63
carbs_g_min: 337
carbs_g_max: 373
since: 2026-09-15
---
```

## Food

Folder `nodes/food/`, flat, one file per Food. Built by ticket
[#24](https://github.com/erodriguezh/food-planner-nutrition/issues/24);
written by `routines/create-food.md`, also when the log, meal or pantry routine meets an unknown Food.

File name = canonical English name with spaces, first word capitalised (`Chicken breast.md`). A packaged product ends with the brand
(`Chicken meatballs Spar.md`); a generic Food has no brand (`Chicken breast.md`).
Every Food sits directly at `nodes/food/<Name>.md`. The lint fails a `type: food` file in another node folder, in a subfolder of `nodes/food/`, or outside `nodes/`.

### Frontmatter

| Property | Type | Required | Meaning |
| --- | --- | --- | --- |
| `type` | text | yes | always `food` |
| `name` | text | yes | canonical English name, equals the file base name |
| `aliases` | list | no | other names the user says; includes the label name |
| `label_name` | text | no | name as printed on the package, often German; must also be an item of `aliases` |
| `brand` | text | no | brand of a packaged product |
| `category` | text | yes | one of `protein`, `dairy`, `grain`, `vegetable`, `fruit`, `fat`, `snack`, `drink` |
| `kcal_per_100g` | number | yes | per 100 g |
| `protein_g_per_100g` | number | yes | per 100 g |
| `fat_g_per_100g` | number | yes | per 100 g |
| `carbs_g_per_100g` | number | yes | per 100 g |
| `fiber_g_per_100g` | number | no | per 100 g, when the source has it |
| `sugar_g_per_100g` | number | no | per 100 g |
| `salt_g_per_100g` | number | no | per 100 g |
| `servings` | list | no | items `"<count> <unit> = <grams> g"`; the first item is the default portion |
| `label_basis` | text | yes | `100g` or `100ml`: what the package states |
| `density_g_per_ml` | number | when `label_basis` is `100ml` or a serving was given in ml | grams per millilitre |
| `density_source` | text | with `density_g_per_ml` only | `label`, `database` or `estimate` |
| `number_source` | text | yes | `label`, `database` or `estimate` |
| `source_ref` | text | no | database name and id, or URL |
| `barcode` | text | no | EAN/GTIN as a quoted string |
| `source_date` | date | yes | day of the scan, lookup or estimate |
| `reviewed` | checkbox | yes | `true` after the user said ok; `false` when the agent wrote the node without an ok |
| `estimated_from` | text | no | `"[[Food]]"` the estimate was scaled from; the only outgoing edge. Required when `number_source` is `estimate`. Stays when label numbers later replace the estimate |

No other property is allowed.

### Rules

- Stored macro values are always per 100 g. A per-100-ml label converts once at creation: per 100 g = per 100 ml ÷ `density_g_per_ml`. The original per-100-ml values are not stored. Water-like liquids (milk, plant drinks, juice) may use `1.0` with `density_source: estimate`; oils and syrups need a real density.
- Rounding rule for Food numbers (macros, fiber, sugar, salt): one decimal, a half rounds up (2.25 → 2.3). Stated in `routines/create-food.md` step 3; the lint applies it in `round_food_value()` and fails a value with more decimals. Density is a conversion factor and may keep two decimals.
- Serving aliases end in grams; ml servings convert with the density at creation (`"1 tbsp = 9 g"` for olive oil). The unit is singular. Any ml to g step, a per-100-ml label or a serving given in ml, stores `density_g_per_ml` and `density_source`, also when `label_basis` is `100g`. The lint cannot see the input unit, so `routines/create-food.md` step 3 is the contract for it.
- Provenance (`number_source`) and review (`reviewed`) are separate. A label read by the agent is unreviewed until the user says ok. "ok" sets `reviewed: true` and changes nothing else; a corrected number is written instead and the Food stays unreviewed. Review never removes an estimate mark; only label or database numbers do.
- Lookup order for missing or generic numbers: Open Food Facts (packaged, barcode), Swiss Food Composition Database (generic, German names), USDA FoodData Central (English), then an estimate from a similar Food with `estimated_from`. The reply names the source.
- A reformulated product overwrites the node and bumps `source_date`. Closed Days keep their totals.
- `number_source: estimate` needs `estimated_from`: an estimate always names the Food it came from. The reverse is not true; `estimated_from` may stay after label or database numbers replace the estimate, so the provenance survives.
- A Food links only through `estimated_from`. Pantry and Meal link to the Food; backlinks give the reverse view.
- Body: optional `## Notes` section only (taste, shop, price). No label transcription.
  The body is either empty or one `## Notes` heading with its content. The lint fails text outside that section (free prose before the first heading included), any other heading at any level, and a second `## Notes` heading.

### Index line

One line per Food under `## Food`: `- [[Name]] | <category> | <aliases plus label name, comma separated>`.
The alias field is the set `aliases` ∪ {`label_name`}; a Food without aliases has the link and category only.
A `label_name` is always one of the `aliases`, so the union adds nothing; the lint fails a Food whose `aliases` omit its `label_name`.
The lint fails on a missing or extra alias, a wrong category, or a second line for the same Food.

### Alias resolution

The Food and Meal lines of the Index form one alias table. Matching is case-insensitive and ignores umlauts
(ä → a, ö → o, ü → u, ß → ss) and plurals (a trailing n, else es, else s is dropped on both sides). Order:
exact canonical name, then alias, then fuzzy. The fuzzy candidates are the union of two sets: the close matches
(difflib, cutoff 0.8) and the forms that start with or contain what the user said. Normalization can map two
different canonical names to one form, so every stage keeps every candidate of that form; a second candidate is
never dropped in silence. One candidate is used, and a fuzzy one is named in the reply. Several candidates: one
Pantry candidate wins; two or more Pantry candidates, or none, and the agent asks. The lint module holds this as
`resolve_name()`, which returns `status`, `name` and the sorted `candidates` of the stage that matched. The
Food-versus-Meal collision rule (ask, except a slot word makes the Meal win) belongs to the log routine and is
not part of `resolve_name()` yet.

### Example

```
---
type: food
name: Soy milk Alpro
aliases:
  - Soya Original
  - Sojadrink
  - soja milk
  - soy milk
label_name: Soya Original
brand: Alpro
category: drink
kcal_per_100g: 39
protein_g_per_100g: 3
fat_g_per_100g: 1.8
carbs_g_per_100g: 2.5
fiber_g_per_100g: 0.5
sugar_g_per_100g: 2.5
salt_g_per_100g: 0.1
servings:
  - "1 glass = 250 g"
label_basis: 100ml
density_g_per_ml: 1.0
density_source: estimate
number_source: database
source_ref: https://world.openfoodfacts.org/product/5411188121923
source_date: 2026-09-15
reviewed: false
---
```

The example is the real node `nodes/food/Soy milk Alpro.md`.

Index line: `- [[Soy milk Alpro]] | drink | Soya Original, Sojadrink, soja milk, soy milk`.

## Pantry

One file, and it is required: `nodes/pantry/Pantry.md`. The lint fails a vault with no Pantry node, with more than one, or with the node at another path. Built by ticket
[#24](https://github.com/erodriguezh/food-planner-nutrition/issues/24);
written by `routines/pantry.md`. The default answer to "what do I have"; the conversation overrides it.

### Frontmatter

| Property | Type | Required | Meaning |
| --- | --- | --- | --- |
| `type` | text | yes | always `pantry` |
| `name` | text | yes | always `Pantry` |
| `updated` | date | yes | day of the last change |
| `staples` | list | no | items `"[[Food]]"`: always available, no amount, no date |
| `items` | list | no | items `"[[Food or Meal]]"`, optionally ` = <amount>`, optionally `, until <YYYY-MM-DD>` |

No other property is allowed.

### Rules

- Amount shapes: a Food in grams (`= 1000 g`); a Meal (leftover) in `= <n> portion` or `= <n> g cooked`. The amount is optional and rough.
- `until` only when the user states a date. The agent never guesses one. Items at or past `until` are flagged in the reply and get priority at plan time.
- Every link resolves to an existing Food (staples) or Food or Meal (items) by canonical name. A name appears at most once across both lists.
- Staple or item is the agent's call from its own knowledge; the user's word overrides it. "Gone" removes the name from whichever list holds it. "Make X a staple" moves it.
- "I bought ..." appends an item; an existing item gets the amounts added when the units match, else the stated amount wins.
- Restock from a receipt, shopping-list or product photo takes exactly one ok: the agent resolves every line, stages the unknown Foods without writing them, and shows one list "Add to Pantry: ... Ok?". Nothing is written before that ok.
- After the ok the agent creates each staged Food as `routines/create-food.md` describes, `reviewed: false`, one commit `create-food: <name>` each and no reply of its own, then applies the additions in one commit `pantry: <one line>`. The restock ok is not a Food review; the new Foods stay unreviewed and the pantry reply names them. Staples in the photo are skipped with a note.
- A chat form ("I bought 1 kg chicken breast") with an unknown Food keeps the create-food path: the Food is written at once with its own reply and its own ok.
- Logging never changes the Pantry.
- One change is one commit `pantry: <one line>`; a restock commits each staged Food first. `updated` is set on every change.
- The Index holds one pointer line under `## Pantry`: `- [[Pantry]]`.
- Body: optional `## Notes` section only, under the same rule as the Food body: empty, or one `## Notes` heading with its content and nothing outside it.

### Example

```
---
type: pantry
name: Pantry
updated: 2026-09-15
staples:
  - "[[Oats]]"
  - "[[Rice]]"
  - "[[Olive oil]]"
items:
  - "[[Skyr]] = 1000 g"
  - "[[Chicken breast]] = 600 g, until 2026-09-18"
  - "[[Blueberries]]"
  - "[[Chili]] = 2 portion, until 2026-09-19"
---
```

## Meal, Day

Written by the tickets that build those nodes. Until then the spec issue
[#22](https://github.com/erodriguezh/food-planner-nutrition/issues/22) is the source.
