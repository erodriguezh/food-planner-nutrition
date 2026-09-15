# create-food

## When
A label photo or a new Food in chat.

## Read
`index.md`, candidate Foods.

## Steps
1. Chat name. Resolve: exact, alias, fuzzy; two ask. A Food hit: a new label overwrites it, bump `source_date`. A Meal hit is not a Food; never overwrite a Meal.
2. Label photo. Identify by `barcode`, `label_name`, `brand`, Foods only: one Food, overwrite it; else, ambiguous too, a new Food. Ask nothing.
3. Canonical English name, a category; brand last frees a taken base name.
4. Numbers /100 g, 1 decimal, half up; label: `number_source: label`. `label_basis: 100ml`: /100 g = /100 ml ÷ density. An ml step stores `density_g_per_ml`, `density_source`, even with `label_basis: 100g`.
5. No label/gap: Open Food Facts, Swiss Food Composition Database, USDA FoodData Central in order; `source_ref`; else estimate, `estimated_from`.
6. `aliases`: label and chat names; `label_name`, `brand`, `barcode`. First `servings` = portion in grams.

## Write
Food `reviewed: false`; its `index.md` line; `state.md`. Commit `create-food: <name>`.

## Reply
"Created <name>: kcal, P, F, C /100 g (<source>). Say ok to mark reviewed."
"ok" sets `reviewed: true`; a correction is written instead.
