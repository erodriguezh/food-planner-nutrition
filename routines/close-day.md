# close-day

## When
"close the day", "done for today", a log dated after the open Day (auto-close).

## Read
The open Day, Goals.

## Steps
1. Day: the open one; none: say so, stop. Auto-close: the older open Day, `status: auto-closed`, before the new Day exists.
2. Table `| slot | kcal | P | F | C |`: one row per slot with an entry, in order, then `| TOTAL | ... |` = Day totals. `estimated: true`: `~` before every table number.
3. Line `Goal <kcal> kcal, <P> P, <F> F, <C> C.` with the Goals targets.
4. Four bullets `- <kcal|protein|fat|carbs> <n> over|under`, in that order; n = the gap to the target, no sign.
5. Verdict, one line: `on target` when all four sit inside min and max, else `off target: <macro> low|high`, one per off macro, comma separated.
6. Last line `Hint: <one line for tomorrow>`, only when useful.
7. Name the unreviewed Foods eaten today. "ok": `reviewed: true` on all, commit `close-day: reviewed <names>`.

## Write
`## Summary` after the slots, `status: closed`, `state.md` `open_day: ""`, `updated`; commit `close-day: <date> <verdict>`.

## Reply
Table, verdict, hint, one line naming the unreviewed Foods (none: no line). `~` on every total when estimated.
