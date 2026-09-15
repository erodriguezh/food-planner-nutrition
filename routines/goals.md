# goals

## When
"Set my goals: 2500 kcal, 135 protein, 60 fat, 355 carbs", "set protein to 160", "tolerance 10 percent".

## Read
`nodes/goals/Goals.md` when it exists.

## Steps
1. Take the targets the user states. Keep the stored value for each target the user did not state. On first setup ask once for the missing ones out of kcal, protein, fat, carbs.
2. `tolerance_pct` is 5 unless the user states one.
3. For each of the four targets compute `<macro>_min = target × (1 − tolerance_pct/100)` and `<macro>_max = target × (1 + tolerance_pct/100)`.
4. Rounding rule: round each bound to the nearest whole number; a half rounds up (137.5 → 138). This is the only place the rule is stated; the lint applies it.
5. Set `since` to today. Every change rewrites all four targets, the tolerance, all eight bounds and `since`. Nothing is recomputed at read time.

## Write
`nodes/goals/Goals.md` (four targets, `tolerance_pct`, eight bounds, `since`); `index.md` Goals line the first time; `state.md` (`updated`).
Commit: `goals: <one line>`, for example `goals: 2500 kcal, 135 P, 60 F, 355 C`.

## Reply
One line with the four targets and the tolerance.
