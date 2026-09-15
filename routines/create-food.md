# create-food

## When
A label photo, "create a food ...", an unknown Food inside a log.

## Read
`index.md` (alias check).

## Steps
1. Pick the canonical English name and a category. Check the name is free.
2. Numbers: from the label when there is a photo; else database order Open Food Facts, Swiss FCDB, USDA; else estimate from a similar Food and set `estimated_from`.
3. Per 100 g. Convert per-100-ml values with a density.
4. Add one default serving when known.
5. Write with `reviewed: false`.

## Write
Food node, `index.md` line.
Commit: `create-food: <name>`.

## Reply
One line: "Created <name>: kcal, P, F, C per 100 g (<source>). Say ok to mark reviewed."
