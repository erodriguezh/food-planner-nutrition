# create-meal

## When
"Save my lunch as ...", "create meal X with ...", "call it ...".

## Read
Food nodes of the ingredients; today's Day when built from entries.

## Steps
1. Resolve names. Unknown Food: follow `routines/create-food.md`.
2. Missing amount: default portion of the Food, else estimate and say so.
3. Sum the totals, set `weight_g`, `portions`, `estimated`, `totals_date`.
4. Show ingredients with grams and totals. Ask "ok?".
5. On ok write `reviewed: true`, else `reviewed: false`.

## Write
Meal node, `index.md` line.
Commit: `create-meal: <name>`.

## Reply
The ingredient list and totals, then one line when written.
