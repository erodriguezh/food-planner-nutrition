# goals

## When
"Set my goals: 2500 kcal, 135 protein, 60 fat, 355 carbs", "set protein to 160", "tolerance 10 percent".

## Read
`nodes/goals/Goals.md` when it exists.

## Steps
1. First setup: take the stated targets, ask once for the missing ones of kcal, protein, fat, carbs. `tolerance_pct` is 5 unless stated.
2. Existing node: change only what the user states. Unnamed targets keep their stored value. An unnamed tolerance keeps the stored `tolerance_pct`, never 5.
3. Compute `<macro>_min = target × (1 − tolerance_pct/100)` and `<macro>_max = target × (1 + tolerance_pct/100)` for all four.
4. Rounding rule: nearest whole number; a half rounds up (137.5 → 138). Stated only here; the lint applies it.
5. Set `since` to today. Every change rewrites all targets, the tolerance, all eight bounds and `since`. Nothing is recomputed at read time.

## Write
`nodes/goals/Goals.md`; `index.md` Goals line the first time; `state.md` (`updated`).
Commit: `goals: <one line>`, for example `goals: protein 160`.

## Reply
One line with the four targets and the tolerance.
