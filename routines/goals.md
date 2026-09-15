# goals

## When
First setup, "set protein to 160", "today 2800 kcal".

## Read
`nodes/goals/Goals.md`.

## Steps
1. Take the targets the user states. Ask for the missing ones out of kcal, protein, fat, carbs.
2. Tolerance 5 unless stated.
3. Compute min and max per macro from target and tolerance.
4. Set `since` to today.

## Write
Goals node (four targets, tolerance, eight min/max); `index.md` line the first time.
Commit: `goals: <one line>`.

## Reply
One line with the four targets.
