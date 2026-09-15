# rebalance

## When
Called by log and close-day. "What is left?", "what should I eat?"

## Read
Today's Day node, `nodes/goals/Goals.md`, `nodes/pantry/Pantry.md`.

## Steps
1. Remaining = target minus running totals, for kcal, protein, fat, carbs.
2. Open slots = slots with no entry, in order breakfast, lunch, snack, dinner. A slot the user removed in chat is not open.
3. Say the remaining numbers. If a macro is over its max, say so.
4. Only on request, suggest the next open slot in full: pantry only, protein category first, then grain, vegetable, fruit, fat. Items with `until` today or tomorrow first, with a note. Servings when the Food has one, else grams rounded to 10 g.
5. One rough line for the later open slots.
6. If the pantry cannot reach protein, say so and add one or two non-pantry options.

## Write
Nothing.

## Reply
After a log: one line, what is left. On request: one suggestion block.
