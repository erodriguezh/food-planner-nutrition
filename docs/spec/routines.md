# Spec: routines

The eight routines under `routines/`, what each reads, does, writes and
replies. Derived from the spec issue
([#22](https://github.com/erodriguezh/food-planner-nutrition/issues/22)) and
assembled by ticket [#28](https://github.com/erodriguezh/food-planner-nutrition/issues/28)
from the tickets that built each routine (#23 goals, #24 create-food and
pantry, #25 log, rebalance and create-meal, #26 close-day and review). The
routine files are the contract the agent reads at runtime; this document
describes them for a rebuild and quotes their fixed strings, so
`lint/test_spec_layout_routines.py` fails when a routine drifts from it. The
agent never loads this document in daily use.

## Common shape

Eight files, one per job, with the same five sections in this order: When
(three example phrases), Read, Steps, Write, Reply. Each file is under 300
tokens (characters divided by four). A routine holds the method, never a
result. Routines chain with "then follow `routines/x.md`"; steps are never
copied between files. Every write ends in one commit per routine step named
`<routine>: <one line>`; a routine that writes nothing makes no commit.

The rounding rule is stated once per thing rounded: Goals bounds in
`routines/goals.md` step 4, Food numbers in `routines/create-food.md` step 4,
entry-line macros and Meal and Day totals in `routines/log.md` step 4. The
lint applies all three.

## The routines

### log

When: "it was 200 g", "remove the snack", "yesterday I had"

Reads the nodes it needs and the Day. Today, else the stated past date; a
closed Day is corrected and the agent says so; an older open Day is
auto-closed first. Names resolve through the alias table; a fuzzy hit is used
and named, two candidates ask, a slot word makes the Meal win; an unknown Food
follows `routines/create-food.md` with its own commit before the log. Slot by
word, else clock (before 11 breakfast, before 15 lunch, before 18 snack, then
dinner), else the next slot in order when the clock slot already has an entry
from an earlier message. A Meal is logged by portion or grams; a stale Meal is
recomputed first; cooked grams convert with `cooked_weight_g`, else the shrink
is guessed, the error said and the line marked. Whole macros on the line, one
decimal for fiber, sugar and salt, a half rounds up. The line is
`- [[Name]] = <n> g — <kcal> kcal · <P> P · <F> F · <C> C`, with `, [[Food]] = <n> g`
for an ingredient change and `- ~ ` for an estimate or a guess. The seven Day
totals and `estimated` are rewritten; the Pantry never changes, and a log over
its amount asks "was that the last of X?". A log into a closed Day ends in the
refresh mode of `routines/close-day.md`.

Writes: a new Day with `status: open` and `goal: "[[Goals]]"`, `state.md`
`open_day`, the Index month line. Commit `log: <date> <slot> <name> <amount>`.
Reply through `routines/rebalance.md`: the slot, the `~`, and "corrected" for a
closed Day.

### rebalance

When: After every log, "what is left?", "what should I eat for lunch?", "plan today".

Reads today's Day, Goals and Pantry. Remaining is target minus running totals
for kcal, protein, fat and carbs, said after every log; a macro over its max is
named with a lighter next slot. Open slots are the slots with no entry, in
order, minus slots removed in chat ("no snack today" writes nothing). A
suggestion comes only on request: "plan today" before the first log covers
every open slot in full; after a log the next slot in full and one rough line
for the rest. Pantry only, protein first, then grain, vegetable, fruit, fat;
items with `until` today or tomorrow first, with a note; servings when the
Food has one, else grams rounded to 10 g. The protein split is the agent's
judgment. Pantry short of protein: one or two non-pantry options. Evening with
lunch open: "did you skip lunch?". `~` on the totals of an estimated Day.

Writes nothing: plans live in the chat, and there is no commit.

### close-day

When: "close the day", "day done", a log into another Day: auto-close, refresh.

Reads the Day, Goals (not in refresh mode) and the Day's Foods and Meals for
`reviewed`. The Summary: the slot table `| slot | kcal | P | F | C |` with one
row per filled slot in order and a `| TOTAL | ... |` row, `~` before every
number of an estimated Day; the goal line
`Goal <kcal> kcal (<min>-<max>), <P> P (<min>-<max>), <F> F (<min>-<max>), <C> C (<min>-<max>).`;
four bullets `- <macro> <n> over|under` in the column order, an exact hit
`0 under`; the verdict `on target` or `off target: <macro> low|high`, one per
off macro; `Hint: <one line>` when useful. Then the unreviewed Foods of the
Day are named; "ok" sets `reviewed: true` on all of them with the commit
`close-day: reviewed <names>`.

Writes `## Summary` after the slots. Close: `status: closed`. Auto-close:
`status: auto-closed`, before the new Day is written. Both clear `state.md`
`open_day` and set `updated`, commit `close-day: <date> <verdict>`. Refresh (a
log into a closed Day): the Summary only, the goal line kept, status and
`open_day` unchanged, no own commit.

### create-food

When: Label photo, "create a food ...", unknown Food.

Reads `index.md` and the candidate nodes. In chat the name resolves exact,
alias, fuzzy; two candidates ask; a Food hit is overwritten by a label with a
bumped `source_date`; a Meal hit is never overwritten. A label photo identifies
the product by `barcode`, then `label_name` with the same `brand`, Foods only:
exactly one Food is overwritten, else a new Food is made, and the Pantry never
breaks the tie; nothing is asked. Canonical English name and category; a
packaged product ends with the brand; the base name is free. Numbers per 100 g,
one decimal, a half rounds up; a `100ml` label divides by the density; any ml
step stores `density_g_per_ml` and `density_source`. Missing numbers come from
Open Food Facts, then the Swiss Food Composition Database, then USDA FoodData
Central, with `source_ref`, else an estimate with `estimated_from`. Aliases
hold the label and chat names; `servings` in grams.

Writes the Food with `reviewed: false`, its `index.md` line and `state.md`.
Commit `create-food: <name>`. Reply
"Created <name>: kcal, P, F, C /100 g (<source>). Say ok to mark reviewed."
"ok" sets `reviewed: true`; a correction is written instead.

### create-meal

When: "skyr, blueberries, oats and soja milk, call it Usual breakfast", "save my lunch as ...", "create meal X with ...".

Reads `index.md`, the ingredient Foods and today's Day when built from entries.
The name must be free of every Food and Meal name. Unknown Foods are created
first through `routines/create-food.md`, one commit each, no reply, one summary
line. A missing amount takes the default portion, else an estimate that is
said. Missing fiber, sugar or salt is filled on the Food first. The Meal sums
its Foods: `weight_g`, the seven totals by the log rounding rule, `totals_date`,
`portions`, `slots`, `aliases`, `estimated`, `cooked_weight_g` only when stated.
The list and totals are shown with one "ok?"; ok sets `reviewed: true`. Built
from today's entries, the Day lines stay as eaten.

Writes the new Foods first, then the Meal, the `index.md` line
`- [[Name]] | <slots or any> | <aliases>` and `state.md`. Commit
`create-meal: <name>`.

### pantry

When: "I bought 1 kg chicken", "eggs are gone", "make rice a staple", a receipt or shopping-list photo.

Reads `nodes/pantry/Pantry.md` and `index.md`. Names resolve; a chat form with
an unknown Food follows `routines/create-food.md`. Staple or item is the
agent's call, the user's word wins. Bought appends, Foods in grams, an existing
item's amount adds up, a staple stays with a note. "Gone" removes; "make X a
staple/item" moves. Leftovers are Meal items in `portion` or `g cooked`, with
`until` only when stated. A photo stages unknown Foods and shows one list
"Add to Pantry: <name amount>, ... Ok?"; nothing is written before the ok.
After the ok each staged Food is created with one `create-food` commit and no
reply, then the additions land; staples are skipped with a note; the ok is not a
Food review. `updated` is today. Logging never changes the Pantry.

Writes the staged Foods with their Index lines, then the Pantry and `state.md`.
Commit `create-food: <name>` each, then `pantry: <one line>`. Reply one line:
changes, expired items, unreviewed Foods.

### goals

When: "Set my goals: 2500 kcal, 135 protein, 60 fat, 355 carbs", "set protein to 160", "tolerance 10 percent".

Reads `nodes/goals/Goals.md` when it exists. First setup takes the stated
targets and asks once for the missing ones; `tolerance_pct` is 5 unless stated.
A later change edits only what the user states; an unnamed tolerance keeps the
stored one. `<macro>_min` and `<macro>_max` are target × (1 ∓ tolerance / 100),
whole numbers, a half rounds up. `since` is today. Every change rewrites all
targets, the tolerance, all eight bounds and `since`.

Writes `nodes/goals/Goals.md`, the `index.md` Goals line the first time, and
`state.md`. Commit `goals: <one line>`, for example `goals: protein 160`.
Reply one line with the four targets and the tolerance.

### review

When: "how was my week", "last week", "review".

Reads the week's Days and Goals. Monday to Sunday; "how was my week" and
"review" mean this week, "last week" the previous one. Eligible dates: this
week Monday to today, last week all seven. Counted Days are the eligible
`closed` and `auto-closed` ones; the week's `open` Day is never counted and is
named in one line; missing dates are stated, never guessed. Average per day is
the seven totals divided by the counted Days, rounded by the log rule. Days on
target are the verdicts reading `on target`. The most common miss is the top
`<macro> low|high` with its day count; ties stay on the one line, `; ` apart,
in the order kcal, protein, fat, carbs, low before high. Nothing counted:
`Average: n/a`, `On target: 0 of 0`, `Most common miss: none`.

Writes nothing and makes no commit. Reply under ten lines:

- `Days: <n> of <eligible> closed, <m> auto-closed, missing <dates|none>`
- `Average: <kcal> kcal · <P> P · <F> F · <C> C · <n> fiber · <n> sugar · <n> salt` (counted Day estimated: `~` before every number)
- `Target: <kcal> kcal · <P> P · <F> F · <C> C`
- `On target: <n> of <days>`
- `Most common miss: <macro> <low|high>, <n> days[; <macro> <low|high>, <n> days]` or `none`
- `<date> is open and not counted.`

## Acceptance run

The seeded-day acceptance run (`acceptance/seeded_day.py`, see
[layout](layout.md)) exercises the routines in ten turns, each turn one
message, on a throwaway branch:

| Turn | Message | Routine | Commit |
| --- | --- | --- | --- |
| 1 | "Plan today for me." | `rebalance` | none |
| 2 | "I had the usual breakfast." | `log` (alias `usual`) | `log: <date> breakfast Usual breakfast 1 portion` |
| 3 | "Also ate a croissant at the office, count it as breakfast." | `create-food`, then `log` with a guessed 60 g and the `~` | `create-food: Croissant`, `log: <date> breakfast Croissant 60 g` |
| 4 | "No snack today." | `rebalance` | none |
| 5 | "What should I eat for lunch?" | `rebalance` | none |
| 6 | "Had that, but 200 g of chicken." | `log` (changed amount) | `log: <date> lunch Chicken breast 200 g, Rice 150 g` |
| 7 | "Dinner: 4 eggs." | `log` (serving to grams) | `log: <date> dinner Eggs 240 g` |
| 8 | "Close the day." | `close-day` | `close-day: <date> off target: kcal low, fat low, carbs low` |
| 9 | "breakfast: the usual" (next day) | `log` (slot word) | `log: <next date> breakfast Usual breakfast 1 portion` |
| 10 | "How was my week?" | `review` | none |

Not exercised by the run: `create-meal`, `pantry`, `goals`, the auto-close and
the refresh mode of `close-day`, and an ingredient change. Their contracts are
pinned by the routine-contract tests under `lint/`.
