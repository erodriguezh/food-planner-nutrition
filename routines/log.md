# log

## When
"I had the usual breakfast", "it was 200 g", "remove the snack", "yesterday I had ...".

## Read
`state.md`, `index.md`, named nodes, Goals, Day.

## Steps
1. Today unless named; a past date writes into its Day; a closed Day: rewrite, keep status, say so; older open Day: auto-close first.
2. Alias table; a fuzzy hit is used and named; two ask; slot word: Meal wins. Unknown Food: `routines/create-food.md`, own commit, then log.
3. Slot: user's word; else clock: <11 breakfast, 11–15 lunch, 15–18 snack, else dinner; filled earlier: next in order.
4. Grams only; Meal by portion or grams. Macros whole, half up; fiber, sugar, salt one decimal.
5. `- [[Name]] = <n> g — <kcal> kcal · <P> P · <F> F · <C> C`; changed ingredient `, [[Food]] = <n> g`, never on the Meal.
6. `- ~ ` after the bullet: estimate or guess. Add, change or remove the line.
7. Rewrite seven totals and `estimated`; never the Pantry; then `routines/rebalance.md`.

## Write
New Day: `status: open`, `goal: "[[Goals]]"`; `state.md` `open_day`; month line on a new month; commit `log: <date> <slot> <name> <amount>`.

## Reply
One line: slot, the entry, what is left (kcal, P, F, C); `~` when estimated.
