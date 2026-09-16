# review

## When
"how was my week", "last week", "review".

## Read
The Days of the week, Goals.

## Steps
1. Week: Monday to Sunday. "This week", "how was my week": the current week so far; "last week": the previous week. No rolling window.
2. Count `status: closed` and `auto-closed` Days only. Today open: leave it out, say so in one line. Missing days: state them, never guess.
3. Average per day = sum of the Day totals ÷ days counted, rounded by `routines/log.md` step 4. `~` on the average when any counted Day is `estimated: true`.
4. Days on target: Summaries whose verdict is `on target`. Most common miss: the `<macro> low|high` most often in the verdicts, with its day count; a tie names each.
5. Compute in chat from the Day files and Goals. Nothing else is read.

## Write
Nothing. No file, no commit.

## Reply
Under ten lines, in this order:
`Days: <n> of 7 closed, <m> auto-closed, missing <dates or none>`
`Average: <kcal> kcal · <P> P · <F> F · <C> C`
`Target: <kcal> kcal · <P> P · <F> F · <C> C`
`On target: <n> of <days>`
`Most common miss: <macro> <low|high>, <n> days` (all on target: `none`)
`Today is open and not counted.` when today is open.
