# log

## When
"I ate ...", "it was 200 g", "remove the snack", "yesterday I had ..."

## Read
`state.md`, `index.md`, the named Food or Meal nodes, `nodes/goals/Goals.md`, the Day node for the date.

## Steps
1. Date: today unless the user names one.
2. If the last open Day is older than the date: set its status `auto-closed`, write its `## Summary`, then continue.
3. Resolve each name with the alias table. Unknown Food: follow `routines/create-food.md`, then continue.
4. Slot: the user's word first. Else the clock: before 11:00 breakfast, 11:00–15:00 lunch, 15:00–18:00 snack, after 18:00 dinner.
5. Convert servings and ml to grams. Compute the line macros from the node.
6. Add, change or remove the entry line. Put `- ~ ` when the Food, the Meal or the amount is estimated.
7. Rewrite the seven totals and `estimated`.
8. Then follow `routines/rebalance.md` for the numbers.

## Write
Day node (create when missing), `state.md` (`open_day`), `index.md` month line on the first log of a month.
Commit: `log: <date> <slot> <name> <amount>`.

## Reply
One line: what was logged with its macros, then what is left today. Name the slot.
