# log

## When
"it was 200 g", "remove the snack", "yesterday I had"

## Read
nodes, Day.

## Steps
1. Today unless named; past date: its Day; closed: say so; older open: auto-close.
2. Alias table; fuzzy hit is used and named, two ask; slot word: Meal wins; new Food: `routines/create-food.md`, own commit, then log.
3. Slot: word, else clock <11 breakfast, <15 lunch, <18 snack, dinner; filled earlier: next in order.
4. Meal: Food `source_date` > `totals_date`: sum its Foods, write the Meal's seven totals, `totals_date`, `estimated` first; cooked g × `weight_g`/`cooked_weight_g`, else guess shrink, say the error, `~`; whole macros, rest one decimal, half up.
5. Add, change or remove a line `- [[Name]] = <n> g — <kcal> kcal · <P> P · <F> F · <C> C`, changed ingredient `, [[Food]] = <n> g`, not on the Meal; `- ~ ` after the bullet: estimate, guess.
6. Rewrite Day totals, `estimated`; never the Pantry, over it: "was that the last of X?".
7. Closed: `routines/close-day.md` refresh.

## Write
New Day `status: open`, `goal: "[[Goals]]"`, `state.md` `open_day`, month line; commit `log: <date> <slot> <name> <amount>`.

## Reply
`routines/rebalance.md`: slot, `~`; closed Day corrected.
