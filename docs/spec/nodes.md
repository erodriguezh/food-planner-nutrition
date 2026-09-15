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
- A goal change in chat rewrites all four targets, the tolerance, all eight bounds and `since`. Nothing is recomputed at read time. Git keeps the history.
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

## Food, Meal, Day, Pantry

Written by the tickets that build those nodes. Until then the spec issue
[#22](https://github.com/erodriguezh/food-planner-nutrition/issues/22) is the source.
