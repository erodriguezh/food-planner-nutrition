# pantry

## When
"I bought 1 kg chicken breast", "eggs are gone", "make rice a staple", a receipt or shopping-list photo.

## Read
`nodes/pantry/Pantry.md`, `index.md`.

## Steps
1. Resolve each name in the alias table. Unknown Food: follow `routines/create-food.md` first.
2. Staple or item by your knowledge (rice, oil, salt: staples; chicken, skyr, leftovers: items). The user's word wins.
3. Bought: append the item, Foods in grams. An existing item gets the amounts added. A staple stays as it is, say so.
4. "Gone" removes it from whichever list holds it. "Make X a staple" moves it.
5. Leftovers are Meal items in `portion` or `g cooked`. `until` only when the user states a date. Flag expired items in the reply.
6. Photos: resolve every line, then show one list "Add to Pantry: <name amount>, ... Ok?". Write after ok. Staples in the photo are skipped with a note.
7. Set `updated` to today. Logging never changes the Pantry.

## Write
Pantry node; new Food nodes with their Index lines; `state.md` (`updated`).
Commit: `pantry: <one line>`, for example `pantry: bought Chicken breast 1000 g`.

## Reply
One line: what changed, plus expired items.
