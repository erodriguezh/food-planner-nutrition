# Context: food planner and nutrition tracker

Glossary of the domain language for this vault. Terms are defined once here and used with the same meaning everywhere: node files, routines, the index, and conversation.

## Nodes

- **Food**: one edible thing with known macros per 100 g. A Food is generic (`Chicken breast`) or packaged (`Chicken meatballs Spar`). Each Food is one markdown file.
- **Meal**: a named combination of Foods in gram amounts. Not yet specified in detail.
- **Day**: one calendar day of planned and logged Meals and Foods, with totals at close. Not yet specified in detail.
- **Goals**: the fixed daily macro target. Not yet specified in detail.
- **Pantry**: what is available to eat right now. Not yet specified in detail.

## Food terms

- **Canonical name**: the English name of a Food. It is the file name and the `name` property. For a packaged product it ends with the brand.
- **Label name**: the product name as printed on the package, often German. Stored in `label_name` and repeated in `aliases`.
- **Alias**: any other name the user says for a Food. Stored in `aliases`. An alias is never a link target; links always use the canonical name.
- **Serving alias**: a named portion that maps to grams, written `<count> <unit> = <grams> g`. The first serving alias is the default portion.
- **Number source**: where the macro numbers came from. One of `label` (read from the package), `database` (a nutrition database lookup), `estimate` (agent estimate from a similar food).
- **Reviewed**: the user looked at the numbers and said ok. Independent of number source: a label read by the agent is unreviewed until the user confirms it.
- **Label basis**: whether the package states values per `100g` or per `100ml`. Stored values are always per 100 g.
- **Density**: grams per millilitre of a liquid Food. Used once, at creation, to convert per-100-ml label values and ml serving aliases to grams. Its origin is recorded with the same vocabulary as number source.
- **Category**: a coarse class of a Food used by rebalance: `protein`, `dairy`, `grain`, `vegetable`, `fruit`, `fat`, `snack`, `drink`.
- **Estimated from**: the Food whose numbers an estimate was copied or scaled from. The only outgoing link a Food holds.

## Units

- **Gram** is the only stored unit for amounts. The user may log grams, servings, or millilitres; the agent converts to grams before anything is written.
