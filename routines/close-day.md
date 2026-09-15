# close-day

## When
"Close the day", "done for today", "that was it".

## Read
Today's Day node, `nodes/goals/Goals.md`, the Food nodes eaten today (for `reviewed`).

## Steps
1. Write `## Summary`: one row per slot with entries plus TOTAL (kcal, protein, fat, carbs); the goal numbers used; one bullet per macro over or under; the verdict.
2. Verdict: `on target` when all four macros sit inside min and max. Else `off target:` plus each macro and `low` or `high`.
3. Put `~` before each total when the Day is `estimated: true`.
4. Set `status: closed`.
5. List Foods eaten today with `reviewed: false` in one line.

## Write
Day node, `state.md` (`open_day` empty).
Commit: `close-day: <date> <verdict>`.

## Reply
The summary table, the verdict, one hint for tomorrow when useful, the unreviewed line.
