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

File name = canonical English name with spaces, in sentence case: the first word is capitalised, proper nouns and brands keep their capitalisation (`Chicken breast.md`, `Soy milk Alpro.md`). A packaged product ends with the brand
(`Chicken meatballs Spar.md`); a generic Food has no brand (`Chicken breast.md`).
Naming term: the spec issue [#22](https://github.com/erodriguezh/food-planner-nutrition/issues/22) writes "title case" for this rule, but every node in the vault is sentence case, so the #22 text needs an owner correction; "sentence case" is the one term used here.
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
- Serving aliases end in grams; ml servings convert with the density at creation (`"1 tbsp = 13.7 g"` for olive oil: a metric tablespoon is 15 ml, 15 × 0.91 = 13.65). The unit is singular. Any ml to g step, a per-100-ml label or a serving given in ml, stores `density_g_per_ml` and `density_source`, also when `label_basis` is `100g`. The lint cannot see the input unit, so `routines/create-food.md` step 3 is the contract for it.
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
exact canonical name, then alias, then fuzzy. The fuzzy candidates are the union of two sets: every close match
(difflib, cutoff 0.8, with no maximum count) and the forms that start with or contain what the user said. Normalization can map two
different canonical names to one form, so every stage keeps every candidate of that form; a second candidate is
never dropped in silence. One candidate is used, and a fuzzy one is named in the reply. Every candidate keeps its
kind (`food` or `meal`). Several candidates of one kind: one Pantry candidate wins; two or more Pantry candidates,
or none, and the agent asks. A Food and a Meal in the same stage always ask, because a Pantry item can be a Food or
a Meal, so the Pantry preference must not decide a Food-versus-Meal collision. The lint module holds this as
`resolve_name()`, which returns `status`, `name`, the sorted `candidates` of the stage that matched, and the `kind`
of the one winner (None when the agent asks). The one exception to the Food-versus-Meal ask, an explicit slot word
that makes the Meal win, belongs to the log routine and comes with ticket #25.

A label photo is the one exception to the ask. Issue #24 requires that a label produces the Food node with no question, so the
package identity decides alone: one Food with the same `barcode`, else the printed `label_name` against the Foods only.
That second stage runs the same exact, alias and fuzzy semantics on the Foods alone, where the forms of a Food are its
canonical name, its aliases and its `label_name`; Meals never take part, so a Meal never blocks the Food the package names.
The first matching stage keeps every Food it found, and the brand then filters them. The printed brand and the brand the
Food carries must agree both ways: a printed brand accepts only a Food of that same brand, because a Food of another brand
and a generic Food with no brand are a different product; and a label that prints no brand keeps only a Food that carries
no brand, because the package never names the brand the Food claims. The fuzzy stage matches a substring, so without that
second half a generic `Milk` label would overwrite `Soy milk Alpro` with no question. A Food that the caller did not hand
over has no brand to compare: a printed brand rejects it, and a label with no brand keeps it, because nothing disagrees.
Exactly one Food left is the package and is reused. Pantry membership never takes part in package identity: the Pantry preference of `resolve_name()` is right for
chat, but it is not package identity, so it must never break a label tie. Zero or several Foods left, an ambiguous name
included, therefore mean a new Food whose name ends with the printed brand (a packaged product ends with the brand), and a
count is added in the last resort, so the new name is free of every existing Food and Meal name. The lint module holds this
as `resolve_label()`, which takes no Pantry argument at all and has its own three statuses: `barcode` and `label` name the
one existing Food, `new` names the Food to create. It never returns `ambiguous` and never returns `none`, and never names a
Meal, so a label never overwrites a Meal and never asks. Both functions collect their stage candidates with one shared
helper, `_stage_candidates()`, which applies no preference of its own.

The ask is a same-stage rule, because the stage order comes first: the first matching stage stops the search, so a name that is exact for one kind beats an alias of the other kind and the agent asks nothing. A Food named exactly what the user said wins over a Meal that carries the same word only as an alias, and an exact Meal name wins over a Food alias the same way. Only the candidates of that one matching stage can collide.

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
- Logging never changes the Pantry; `routines/log.md` step 6 holds the one question it may ask.
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

## Meal

Folder `nodes/meal/`, flat, one file per Meal. Built by ticket
[#25](https://github.com/erodriguezh/food-planner-nutrition/issues/25);
written by `routines/create-meal.md`. A Meal exists only when the user names it; an unnamed combination stays on the Day.
The file is named after the Meal in sentence case (`Usual breakfast.md`), free of every Food and Meal name. The lint fails a
`type: meal` file outside `nodes/meal/` or in a subfolder of it.

### Frontmatter

| Property | Type | Required | Meaning |
| --- | --- | --- | --- |
| `type` | text | yes | always `meal` |
| `name` | text | yes | equals the file base name |
| `aliases` | list | no | other names the user says |
| `slots` | list | no | subset of `breakfast`, `lunch`, `snack`, `dinner`, each at most once; absent means any slot |
| `ingredients` | list | yes | items `"[[Food]] = <grams> g"`, one item per Food, at least one; Foods only, a Meal never contains a Meal |
| `portions` | number | yes | how many equal portions the Meal makes, above 0; default 1 |
| `weight_g` | number | yes | the raw sum of the ingredient grams |
| `kcal`, `protein_g`, `fat_g`, `carbs_g` | number | yes | totals of the whole Meal, whole numbers |
| `fiber_g`, `sugar_g`, `salt_g` | number | yes | totals of the whole Meal, one decimal |
| `totals_date` | date | yes | the day the totals were last computed |
| `estimated` | checkbox | yes | `true` exactly when an ingredient Food has `number_source: estimate` |
| `reviewed` | checkbox | yes | `true` after the user's ok to the shown ingredient list |
| `cooked_weight_g` | number | no | the weight after cooking, written once when the user weighed it |

No other property is allowed. There is no `number_source` on a Meal; the ingredient Foods carry it.

### Rules

- Totals are stored, computed from the Food nodes: for each ingredient the per-100-g values times the grams, all added up. The lint recomputes them and fails a stored total that is not the exact value rounded, so a Meal whose Food changed after `totals_date` fails until the agent recomputes it (story 32). The rounding rule is stated in `routines/log.md` step 4 and applied by the lint in `round_total()` (kcal, protein, fat, carbs: whole number, a half rounds up) and `round_food_value()` (fiber, sugar, salt: one decimal, a half rounds up); `matches_rounding()` compares a stored value against the rounded one exactly, so an unrounded value fails and a half has one correct neighbour, not two. The arithmetic itself is decimal: the per-100-g values and the grams are read with `Decimal(str)`, and the scaling, the portion division and the sum stay decimal, so 9.2 per 100 g of 375 g is exactly 34.5 and stores 35 (in binary floats it is 34.49999999999999 and would store 34).
- Every ingredient Food carries `fiber_g_per_100g`, `sugar_g_per_100g` and `salt_g_per_100g`; a missing one is filled and written to the Food before the Meal sums it. The lint fails a Meal whose ingredient Food lacks one.
- `weight_g` equals the ingredient sum exactly; `cooked_weight_g` is stored only when stated.
- Stale Meal: a Meal is stale when an ingredient Food has a `source_date` newer than the Meal's `totals_date`, whether or not the numbers moved. The lint fails it, and `routines/log.md` step 4 recomputes the seven totals, `totals_date` and `estimated` from the Food nodes and writes the Meal before the log uses it (story 32).
- Cooked-weight conversion: an amount the user gives in cooked grams becomes canonical grams as cooked grams × `weight_g` / `cooked_weight_g` before the entry line is written, so the Day line always carries canonical grams. Without `cooked_weight_g` the agent estimates the shrink, states the error in the reply and marks the entry `~`, which makes the Day `estimated` (stories 37 and 38). `routines/log.md` step 4 converts; the lint has no converter of its own.
- Estimation mark: `estimated` is derived, `true` exactly when an ingredient Food is an estimate. It bubbles to the Day entry line as `- ~ ` when the Meal is logged. The user's ok never changes it.
- Unknown Foods in a create-meal flow are created unreviewed first, one `create-food: <name>` commit each with no reply of their own, and named in one summary line; the Meal's one "ok?" sets the Meal `reviewed: true` and touches no Food. A corrected amount is written instead of the ok.
- A Meal built from today's entries leaves the Day lines as they were eaten.
- Edges: Meal to Food only. Body: optional `## Prepare` and `## Notes` sections, in that order, filled only on request; the lint fails any other heading, a second copy, the wrong order and text before the first heading.
- The lint sums the ingredients with `compute_meal()` and compares the stored totals against that sum. Writing the Meal and its Index line belongs to `routines/create-meal.md`, not to the lint.

### Index line

One line per Meal under `## Meal`: `- [[Name]] | <slots, comma separated, or any> | <aliases, comma separated>`.
A Meal without aliases has the link and the slots only. The lint fails a wrong slot field, a missing or extra alias, or a second line.

### Example

```
---
type: meal
name: Usual breakfast
aliases:
  - usual
  - the usual
slots:
  - breakfast
ingredients:
  - "[[Skyr]] = 300 g"
  - "[[Blueberries]] = 150 g"
  - "[[Oats]] = 60 g"
  - "[[Soy milk Milsani]] = 100 g"
portions: 1
weight_g: 610
kcal: 540
protein_g: 46
fat_g: 7
carbs_g: 67
fiber_g: 9.1
sugar_g: 30.6
salt_g: 0.4
totals_date: 2026-09-15
estimated: false
reviewed: true
---
```

The example is the real node `nodes/meal/Usual breakfast.md`. Index line: `- [[Usual breakfast]] | breakfast | usual, the usual`.

## Day

Path `nodes/day/<YYYY-MM>/<YYYY-MM-DD>.md`: one folder per month, one file per date. Built by ticket
[#25](https://github.com/erodriguezh/food-planner-nutrition/issues/25);
written by `routines/log.md`, closed by `routines/close-day.md` (ticket #26). A Day is created at the first log of its date;
a date with no log has no file. Plans are never stored on a Day. The lint fails a Day outside its month folder.

### Frontmatter

All properties are required; no other property is allowed.

| Property | Type | Meaning |
| --- | --- | --- |
| `type` | text | always `day` |
| `name` | text | the date, equals the file base name |
| `date` | date | the date, equals `name` |
| `status` | text | `open`, `closed` or `auto-closed` |
| `goal` | text | always `"[[Goals]]"`, the only frontmatter edge |
| `kcal`, `protein_g`, `fat_g`, `carbs_g` | number | running totals, the sum of the entry lines |
| `fiber_g`, `sugar_g`, `salt_g` | number | running totals from the nodes, one decimal |
| `estimated` | checkbox | `true` exactly when an entry line carries the `~` mark |

### Body

Slot sections `## Breakfast`, `## Lunch`, `## Snack`, `## Dinner` in this fixed order, each present only when it has at least one entry line and holding entry lines only. Then `## Summary`, written when the Day is closed, then optional `## Notes`. The lint fails any other heading, a slot twice, a slot out of order, an empty slot section, text before the first heading and a non-entry line under a slot.

An open Day has no `## Summary`; a closed or auto-closed Day has one, and the lint fails either way round. Its shape is the next section.

### Summary

Written by `routines/close-day.md` (ticket #26) when the user closes the day, or by the auto-close when a log for a later date arrives; rewritten by a log into a closed Day. The non-empty lines of `## Summary` come in this fixed order:

1. The slot table, header `| slot | kcal | P | F | C |`, then one row per slot that has an entry, in the slot order, then the `| TOTAL | <kcal> | <P> | <F> | <C> |` row. A slot row is the sum of that slot's entry lines; the TOTAL row equals the Day totals. Every table number carries the `~` exactly when the Day is estimated (`| TOTAL | ~1307 | ~69 | ~4 | ~249 |`); a plain Day carries none.
2. The goal line `Goal <kcal> kcal, <P> P, <F> F, <C> C.` with the four targets used at close, each as written on the Goals node, a whole number or a decimal. It records the targets, so a later goal change leaves the Day valid; the lint does not compare it with today's Goals.
3. Four bullets `- <macro> <n> over|under`, in the order `kcal`, `protein`, `fat`, `carbs`, with `<n>` the gap between the TOTAL row and the goal line, no sign. A target and a gap take the number grammar of the vault, digits with at most one dot and no sign, so a target of `135.5 P` gives the gap `- protein 66.5 under`, while the table numbers stay whole, because an entry line is rounded whole. A gap has one spelling, the shortest one: against a whole target it is whole, `66` and not `66.0`. A macro that hits its target exactly writes `- <macro> 0 under`; `0 over` fails.
4. The verdict in fixed words: `on target` when all four macros sit inside min and max, else `off target:` and each macro that is off with `low` or `high`, comma separated (`off target: kcal low, protein low`). A `high` macro is `over` in its bullet, a `low` one `under`. The bounds are not on the file, so the lint checks the words and the directions, not the bounds.
5. At most one line `Hint: <one line for tomorrow>`, only when useful.

The lint fails a closed or auto-closed Day whose Summary misses the TOTAL row, the goal line, one of the four bullets or the verdict, holds a free-text verdict, a `protein_g`-style macro word, a `0 over` bullet, a table number that differs from the lines, a `~` that does not match `estimated`, or any other line. The macro words `kcal`, `protein`, `fat`, `carbs` are the column order; the Day properties they report on are `kcal`, `protein_g`, `fat_g`, `carbs_g`.

```
## Summary

| slot | kcal | P | F | C |
| --- | --- | --- | --- | --- |
| breakfast | ~784 | ~51 | ~20 | ~95 |
| TOTAL | ~784 | ~51 | ~20 | ~95 |

Goal 2500 kcal, 135 P, 60 F, 355 C.

- kcal 1716 under
- protein 84 under
- fat 40 under
- carbs 260 under

off target: kcal low, protein low, fat low, carbs low

Hint: three more slots tomorrow.
```

The reply of the close repeats the table, the verdict and the hint, with the `~` on every total of an estimated Day, and ends with one line naming the Foods eaten today that are still unreviewed; "ok" sets `reviewed: true` on all of them. The lint does not see the reply.

### Entry line

Canonical shapes, confirmed by the prototype branch:

```
- [[<Meal or Food>]] = <amount> — <kcal> kcal · <protein> P · <fat> F · <carbs> C
- ~ [[<Meal or Food>]] = <amount> — ...                (estimated input)
- [[<Meal>]] = <n> portion, [[<Food>]] = <n> g — ...    (ingredient change)
```

- `<amount>` is `<n> g` for a Food, `<n> g` or `<n> portion` for a Meal. Servings and millilitres convert to grams before the write. Several snacks are several lines. No time on the line, no checkbox, no italics.
- The four macros are computed from the node at write time by the rounding rule in `routines/log.md` step 4: a Food from its per-100-g values times the grams; a Meal from its stored totals times portions / `portions` or times grams / `weight_g`. The Day is readable without opening the Foods.
- Ingredient change: a Meal by portion whose one ingredient amount differs from the Meal node. The change is written on the line, after the amount, and never on the Meal. The grams on the line are what was on the plate: the macros are the eaten portions of the stored Meal totals, minus the eaten portions of the ingredient as the Meal lists it, plus the amount eaten. For a one-portion Meal that is the stored totals minus the listed ingredient plus the eaten one; for a two-portion Meal listing 200 g skyr, "1 portion with 300 g skyr" replaces 100 g by 300 g. The lint fails a change on a Food entry, on a Meal by grams, or on a changed link that is missing or not a Food, on every Day; that the changed Food is still an ingredient of the Meal is checked on an open Day only.
- Estimation mark: `~` right after the bullet, before the link, and nowhere else. It is written when the Food is an estimate (`number_source: estimate`), when the Meal is estimated (`estimated: true`), or when the agent guessed the amount. The lint requires the mark for an estimated Food or Meal on an open Day and accepts it on a plain node (a guessed amount); on a closed or auto-closed Day the mark is history and stays as written, so a Food that becomes an estimate later never makes an old unmarked line fail. The Day `estimated` is `true` exactly when a line carries the mark, and the chat totals then carry `~`.
- The lint reads the line with `parse_entry_line()`, checks its shape with `check_entry_shape()` on every Day, and recomputes it with `entry_totals()` on an open Day. The vault files are the seam: the routine text tells the agent what to write, the lint judges what is on disk, and the lint holds no second implementation of the routine.
- History, on a closed or auto-closed Day, freezes what the line recorded: its four macros, its `~` and the Meal composition it was written against. It never makes a malformed line valid, so the canonical shape still fails there: a Food by portion, a change on a Food, a change on a Meal by grams, and a changed link that is missing or not a Food. A changed link whose node does not exist fails on a closed Day as the entry's own link does.

### Totals

- `kcal`, `protein_g`, `fat_g`, `carbs_g` equal the sum of the entry lines exactly, on every Day. A closed or auto-closed Day keeps its totals when a Food is reformulated later.
- An open Day is the one being written now, so its entry lines must also equal their nodes by the rounding rule, and `fiber_g`, `sugar_g`, `salt_g` equal the exact sum over the nodes rounded once to one decimal. The lint checks both on `status: open` only.

### Slot rule

The slot is picked by the user's word, else by the clock (before 11:00 breakfast, 11:00 to 15:00 lunch, 15:00 to 18:00 snack, after 18:00 dinner), else, when the clock slot already has an entry from an earlier message, the next slot in order that has none; after dinner there is no next slot. The reply names the slot so a wrong slot is corrected at once. The rule lives in `routines/log.md` step 3; the lint sees only which section a line landed in.
The fixed order is breakfast, lunch, snack, dinner, so the next slot after a filled breakfast is lunch. The story 50 example in #22 ("a 10:15 croissant after breakfast lands under Snack") does not follow from that order; the owner settled it on PR #31 in favour of the fixed order, and the word "snack" in the log still picks the slot.

Alias resolution at log time uses the shared table with one exception: a slot word in the log makes the Meal win a Food-versus-Meal collision (`resolve_name(..., slot_word=True)`).

### Lifecycle, State and Index

- The first log of a date creates the Day with `status: open`, sets the State `open_day` to its link and, on the first log of a month, adds the Index month line `- <YYYY-MM> | nodes/day/<YYYY-MM>/`, all in one commit `log: <date> <slot> <name> <amount>`. An unknown Food inside a log is created first in its own `create-food: <name>` commit.
- A log for a past date writes into that Day. A log into a closed Day rewrites the totals and, through the refresh mode of `routines/close-day.md`, the Summary; it keeps the status and the State, rides on the `log:` commit, and the agent says so. A log for a later date auto-closes the older open Day first, with `status: auto-closed` and the same Summary; the auto-close belongs to `routines/close-day.md` (ticket #26), and the lint holds the invariant.
- The State names the one open Day; the lint fails two open Days, an `open_day` that points elsewhere and an `open_day` that still names a closed or auto-closed Day: the close clears it in the same commit, `close-day: <date> <verdict>`. Every existing `nodes/day/<YYYY-MM>/` folder has exactly one Index month line.
- Logging never changes the Pantry. When the logged amount of a Food is more than the Pantry records for that Food, the agent asks "was that the last of X?" and still writes nothing to the Pantry; with no amount recorded the question does not come up (story 59).

### Review

The weekly review (`routines/review.md`, ticket #26) is computed in chat from the Day files of one calendar week, Monday to Sunday, and the Goals node. It writes nothing, so the lint has nothing to check; the routine text is the contract. It counts `closed` and `auto-closed` Days only, states the missing days and the auto-closed count, leaves an open Day out with one line, gives the average per day against the target on two lines, the days whose verdict reads `on target`, and the most common `<macro> low|high` of the verdicts with its day count. The average carries the `~` when any counted Day is estimated. The whole reply is under ten lines.

The denominator is the eligible dates of the week, not the calendar seven: Monday to today for the current week, all seven for a past one, so a Wednesday review reads `Days: 2 of 3 closed` and a date still to come is never missing. A missing day is an eligible date with no `closed` or `auto-closed` Day. A week with nothing counted has no divisor, so the reply takes the fixed shape `Average: n/a`, `On target: 0 of 0` and `Most common miss: none`.

### Example

```
---
type: day
name: 2026-09-15
date: 2026-09-15
status: open
goal: "[[Goals]]"
kcal: 784
protein_g: 51
fat_g: 20
carbs_g: 95
fiber_g: 11
sugar_g: 34.6
salt_g: 0.7
estimated: true
---

## Breakfast

- [[Usual breakfast]] = 1 portion — 540 kcal · 46 P · 7 F · 67 C
- ~ [[Croissant]] = 60 g — 244 kcal · 5 P · 13 F · 28 C
```

The Croissant line is marked because the 60 g came from a serving the agent guessed; the Day is therefore estimated. There is no Day node on `main` yet: a Day exists only after the first log.
