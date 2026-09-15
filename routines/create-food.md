# create-food

## When
A label photo, "create a food ...", an unknown Food.

## Read
`index.md`.

## Steps
1. Resolve the name: exact, alias, one fuzzy hit; no case, umlaut, plural. A hit: the Food exists; a new label overwrites it, bump `source_date`.
2. Pick the canonical English name (packaged: brand last), a category; base name free. Ask nothing.
3. Numbers per 100 g, one decimal, a half rounds up. Label: `number_source: label`; `label_basis: 100ml` gives per 100 g = per 100 ml ÷ density. Any ml to g step, label or serving, stores `density_g_per_ml` and `density_source`, even with `label_basis: 100g`.
4. No label/gap: Open Food Facts, Swiss Food Composition Database, USDA in order, set `source_ref`; else estimate from a similar Food, `estimated_from`.
5. `aliases`: label and chat names; `label_name`, `brand`, `barcode` if read. First `servings` item = default portion in grams.

## Write
Food node `reviewed: false`; `index.md` line: link, category, aliases plus label name; `state.md`.
Commit: `create-food: <name>`.

## Reply
"Created <name>: kcal, P, F, C per 100 g (<source>). Say ok to mark reviewed."
"ok" sets `reviewed: true` only; a corrected number is written instead.
