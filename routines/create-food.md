# create-food

## When
Label photo, "create a food ...", unknown Food.

## Read
`index.md`, candidates.

## Steps
1. In chat. Resolve: exact, alias, fuzzy; two ask. A Food hit: a label overwrites it, bump `source_date`. A Meal hit is not a Food; never overwrite a Meal.
2. Label photo. Identify: `barcode`, `label_name` as in 1 + same `brand`, Foods only. Exactly one Food: overwrite it; zero or several, ambiguous: new Food; Pantry no tie-break. Ask nothing.
3. Canonical English name, category; packaged: brand last, base name free.
4. Numbers /100 g, 1 decimal, half up; label: `number_source: label`. `label_basis: 100ml`: ÷ density for /100 g. ml step: `density_g_per_ml`, `density_source`, at `label_basis: 100g` too.
5. No label/gap: Open Food Facts → Swiss Food Composition Database → USDA FoodData Central; `source_ref`; else estimate, `estimated_from`.
6. `aliases`: label, chat names; `label_name`, `brand`, `barcode`. `servings` 1 = portion in grams.

## Write
Food `reviewed: false`; the `index.md` line; `state.md`. Commit `create-food: <name>`.

## Reply
"Created <name>: kcal, P, F, C /100 g (<source>). Say ok to mark reviewed."
"ok": `reviewed: true`; a correction instead.
