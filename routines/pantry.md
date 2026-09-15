# pantry

## When
"I bought 1 kg chicken", "eggs are gone", "make rice a staple", a receipt or shopping-list photo.

## Read
`nodes/pantry/Pantry.md`, `index.md`.

## Steps
1. Resolve each name. Chat form, unknown Food: then follow `routines/create-food.md`.
2. Staple or item by your knowledge (oil staple, chicken item); the user's word wins.
3. Bought: append it, Foods in grams; an existing item's amount adds up; a staple stays, say so.
4. "Gone" removes it from its list; "make X a staple/item" moves it.
5. Leftovers are Meal items in `portion` or `g cooked`; `until` if stated.
6. Photo: resolve each line, stage unknown Foods, show one list "Add to Pantry: <name amount>, ... Ok?". Write nothing before the ok.
7. After the ok: create each staged Food by `create-food`, one commit each, no reply, then step 3. Staples are skipped with a note. This ok is not a Food review: they keep `reviewed: false`.
8. `updated` is today. Logging never changes the Pantry.

## Write
Staged Foods with Index lines, then Pantry; `state.md`. Commit `create-food: <name>` each, then `pantry: <one line>`.

## Reply
One line: changes, expired items, unreviewed Foods.
