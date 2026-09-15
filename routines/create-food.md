# create-food

## When
A label photo, "create a food ...", an unknown Food.

## Read
`index.md` (alias table).

## Steps
1. Resolve the name in the alias table: no case, umlauts or plurals; exact, alias, one fuzzy hit. A hit: the Food exists; a new label overwrites it, bump `source_date`.
2. Pick the canonical English name (brand last if packaged) and a category. The base name must be free. Ask nothing.
3. Numbers per 100 g, one decimal, a half rounds up. Label: `number_source: label`. Per 100 ml: `label_basis: 100ml`, `density_g_per_ml`, `density_source`; per 100 g = per 100 ml ÷ density.
4. No label or a gap: Open Food Facts, Swiss Food Composition Database, USDA in order; set `source_ref`. Else estimate from a similar Food, set `estimated_from`.
5. `aliases`: label and chat names; `label_name`, `brand`, `barcode` when read. First `servings` item = default portion, in grams.

## Write
Food node, `reviewed: false`; `index.md` line: link, category, aliases plus label name; `state.md`.
Commit: `create-food: <name>`.

## Reply
"Created <name>: kcal, P, F, C per 100 g (<source>). Say ok to mark reviewed."
"ok" sets `reviewed: true` only. A corrected number is written instead.
