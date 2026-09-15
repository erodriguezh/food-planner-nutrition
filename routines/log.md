# log

## When
"it was 200 g", "remove the snack", "yesterday I had ...".

## Read
`state.md`, `index.md`, nodes, Day.

## Steps
1. Today unless named; past date: its Day; closed Day: rewrite Summary, keep status, say so; older open: auto-close.
2. A fuzzy hit is used and named, two ask; slot word: Meal wins; unknown Food: `routines/create-food.md`, own commit, then log.
3. Slot: the word, else clock (<11 breakfast, 11–15 lunch, 15–18 snack, else dinner); filled earlier: next in order.
4. Meal by portion or grams; Food newer than `totals_date`: recompute it; cooked grams × `weight_g` / `cooked_weight_g`, else guess the shrink, say the error, `~`; macros whole, fiber, sugar, salt one decimal, half up.
5. `- [[Name]] = <n> g — <kcal> kcal · <P> P · <F> F · <C> C`, changed ingredient `, [[Food]] = <n> g`, never on the Meal; `- ~ ` after the bullet: estimate or guess.
6. Rewrite seven totals and `estimated`; never the Pantry, over its amount ask "was that the last of X?"; then `routines/rebalance.md`.

## Write
New Day `status: open`, `state.md` `open_day`, month line; commit `log: <date> <slot> <name> <amount>`.

## Reply
One line: slot, entry, what is left, `~` if estimated.
