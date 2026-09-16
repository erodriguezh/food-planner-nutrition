# review

## When
"how was my week", "last week", "review".

## Read
The Days of the week, Goals.

## Steps
1. Week: Monday to Sunday, no rolling window; "last week" is the previous one. Eligible dates: this week Monday to today, last week all seven; future dates never missing.
2. Count `status: closed` and `auto-closed` Days only. Today open: left out, say so in one line. Missing: eligible dates with no such Day; state them, never guess.
3. Average per day = totals ÷ days counted, rounded by `routines/log.md` step 4; `~` on the average when a counted Day is `estimated: true`.
4. Days on target: verdicts reading `on target`. Most common miss: the most frequent `<macro> low|high`, its day count; a tie names each.
5. None counted: `Average: n/a`, `On target: 0 of 0`, `Most common miss: none`.

## Write
Nothing. No file, no commit.

## Reply
Under ten lines, in order:
`Days: <n> of <eligible> closed, <m> auto-closed, missing <dates or none>`
`Average: <kcal> kcal · <P> P · <F> F · <C> C`
`Target: <kcal> kcal · <P> P · <F> F · <C> C`
`On target: <n> of <days>`
`Most common miss: <macro> <low|high>, <n> days` (all on target: `none`)
`Today is open and not counted.` when it is open.
