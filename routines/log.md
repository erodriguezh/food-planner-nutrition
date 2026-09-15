# log

## When
"it was 200 g", "remove the snack", "yesterday I had"

## Read
`state.md`, `index.md`, nodes, Day.

## Steps
1. Today unless named; past date: its Day; closed Day: rewrite Summary, keep status, say so; older open: auto-close.
2. Alias table; a fuzzy hit is used and named, two ask; slot word: Meal wins; new Food: `routines/create-food.md`, own commit, then log.
3. Slot: word, else clock: <11 breakfast, <15 lunch, <18 snack, else dinner; filled earlier: next in order.
4. Meal by portion or g; Food newer than `totals_date`: rewrite the Meal; cooked g × `weight_g` / `cooked_weight_g`, else guess shrink, say the error, `~`; macros whole, fiber, sugar, salt one decimal, half up.
5. Add, change or remove a line `- [[Name]] = <n> g — <kcal> kcal · <P> P · <F> F · <C> C`, changed ingredient `, [[Food]] = <n> g`, not on the Meal; `- ~ ` after the bullet: estimate or guess.
6. Rewrite seven totals, `estimated`; never the Pantry, over its amount: "was that the last of X?".

## Write
New Day `status: open`, `goal: "[[Goals]]"`, `state.md` `open_day`, month line; commit `log: <date> <slot> <name> <amount>`.

## Reply
`routines/rebalance.md`: one line, slot, what is left, `~`.
