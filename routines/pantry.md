# pantry

## When
"I bought ...", "eggs are gone", "make rice a staple", receipt or shopping-list photos.

## Read
`nodes/pantry/Pantry.md`, `index.md`.

## Steps
1. Staple or item: from your knowledge (rice, oil, salt are staples; chicken, milk, leftovers are items). The user can override.
2. "Gone" removes the thing from whichever list holds it.
3. Unknown Food: follow `routines/create-food.md`.
4. Photos: show one list "Add to Pantry: ...". Write after ok. Add amounts to existing items.
5. Set `updated`.

## Write
Pantry node; new Food nodes when needed.
Commit: `pantry: <one line>`.

## Reply
One line: what changed.
