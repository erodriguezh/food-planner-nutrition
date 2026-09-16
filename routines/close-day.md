# close-day

## When
"close the day", "done for today", a later-dated log (auto-close).

## Read
The Day, Goals, its Foods (Meals too) for `reviewed`.

## Steps
1. Day: the open one; none: say so, stop.
2. Table `| slot | kcal | P | F | C |`: a row per filled slot in order, then `| TOTAL | ... |` = Day totals; `estimated: true`: `~` before every number.
3. `Goal <kcal> kcal, <P> P, <F> F, <C> C.` from the Goals targets.
4. Four bullets `- <kcal|protein|fat|carbs> <n> over|under`, in that order; n = the gap, no sign, the target's decimals only; exact hit `0 under`.
5. Verdict: `on target` when all four inside min and max, else `off target: <macro> low|high`, one per off macro, comma separated.
6. Last line `Hint: <one line>`, only when useful.
7. Name the unreviewed Foods; "ok": `reviewed: true` on all, commit `close-day: reviewed <names>`.

## Write
`## Summary` after the slots, `updated`. Close: `status: closed`. Auto-close: the older open Day, `status: auto-closed`, before the new Day. Both: `state.md` `open_day: ""`, commit `close-day: <date> <verdict>`. Refresh: Summary only; status, `open_day` stay; no commit.

## Reply
Table, verdict, hint, step 7's line (none: no line).
