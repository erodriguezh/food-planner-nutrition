# create-meal

## When
"skyr, blueberries, oats and soja milk, call it Usual breakfast", "save my lunch as ...", "create meal X with ...".

## Read
`index.md`, the ingredient Foods; today's Day when built from entries.

## Steps
1. Name free of every Food and Meal name, else ask another. Resolve Foods by the alias table.
2. Unknown Foods: `routines/create-food.md` each, `reviewed: false`, one commit each, no reply; one summary line.
3. Missing amount: the default portion, else estimate and say so. Missing fiber, sugar or salt: fill the Food first.
4. Sum the Food nodes: `weight_g`, seven totals (rounding as `routines/log.md` step 4), `totals_date`, `portions` (default 1), `slots`, `aliases`; `estimated` when an ingredient is an estimate; `cooked_weight_g` only when stated.
5. Show grams per ingredient and the totals; ask "ok?" once. ok: `reviewed: true`; a correction is written instead.
6. Built from today's entries: Day lines stay as eaten. Prepare, Notes on request.

## Write
New Foods first; Meal; `index.md` line `- [[Name]] | <slots or any> | <aliases>`; `state.md`. Commit `create-meal: <name>`.

## Reply
List, totals, "ok?", new Foods in one line; one line when written.
