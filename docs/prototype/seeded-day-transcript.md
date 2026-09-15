# Prototype: one seeded day end to end

Throwaway. Answers wayfinder ticket #11: does the designed vault feel right in use?
Date of the day: 2026-09-15. Goals: 2500 kcal · 135 P · 60 F · 355 C, tolerance 5 %.
Seed: Goals, Pantry, six Foods (Skyr, Blueberries, Oats, Soja milk Alpro, Chicken meatballs Spar, Rice), one Meal (Usual breakfast). The ticket said five Foods; Rice is the sixth because the Pantry lists it as a staple and a staple needs a node.

Every turn shows: what you said, what the agent read, what it wrote, what it said back. One commit per write step (see `git log`).

---

## Turn 1 · 08:10 · "Plan today for me."

**Read**: `ROUTER.md`, `state.md` (no open day), `index.md`, `nodes/goals/Goals.md`, `nodes/pantry/Pantry.md`, `routines/rebalance.md`, `nodes/meal/Usual breakfast.md`.

**Wrote**: nothing. Plans are never stored.

**Said**:
> Nothing logged yet, so all of today is left: 2500 kcal · 135 P · 60 F · 355 C.
> **Breakfast**: [[Usual breakfast]], 1 portion — 428 kcal · 34 P · 7 F · 56 C. Everything is in the pantry.
> Lunch then needs about 45 g protein and 800 kcal; the meatballs expire tomorrow. Snack about 15 g protein. Dinner about 40 g protein and 700 kcal.

---

## Turn 2 · 08:30 · "I had the usual breakfast."

**Read**: `state.md`, `index.md` (alias "usual" → Usual breakfast), `nodes/meal/Usual breakfast.md`, `nodes/goals/Goals.md`, `routines/log.md`.

**Wrote**:
- `nodes/day/2026-09/2026-09-15.md` created, status `open`, one line under `## Breakfast`, totals 428 · 34 · 7 · 56.
- `state.md`: `open_day: "[[2026-09-15]]"`.
- `index.md`: month line `- 2026-09 | nodes/day/2026-09/`.

Commit: `log: 2026-09-15 breakfast Usual breakfast 1 portion`

**Said**:
> Logged breakfast: Usual breakfast, 1 portion — 428 kcal · 34 P · 7 F · 56 C. Left today: 2072 kcal · 101 P · 53 F · 299 C.

---

## Turn 3 · 10:15 · "Also ate a croissant at the office."

**Read**: `index.md` (no match for "croissant"), `routines/create-food.md`, then `routines/log.md`.

**Wrote**:
- `nodes/food/Croissant.md`: generic, Swiss FCDB values, `1 piece = 60 g`, `reviewed: false`.
- `index.md`: Food line for Croissant.
- Day node: second breakfast line `- ~ [[Croissant]] = 60 g — 244 kcal · 5 P · 13 F · 28 C`, totals 672 · 39 · 20 · 84, `estimated: true`.

Commits: `create-food: Croissant`, then `log: 2026-09-15 breakfast Croissant 60 g`

**Said**:
> Created Croissant: 406 kcal · 8 P · 21 F · 46 C per 100 g (database). Say ok to mark reviewed.
> Logged breakfast: ~ Croissant 60 g — 244 kcal · 5 P · 13 F · 28 C. Left today: ~1828 kcal · 96 P · 40 F · 271 C.

Two things the rules decided here:
- 10:15 is before 11:00, so the croissant went under **Breakfast**, not Snack.
- The 60 g came from a serving the agent made up, so the line carries `~`.

---

## Turn 4 · 12:40 · "No snack today."

**Read**: nothing new.

**Wrote**: nothing. There is no field for a removed slot in the Day node or in `state.md`.

**Said**:
> Ok. Open slots today: lunch, dinner. Left today: ~1828 kcal · 96 P · 40 F · 271 C.

Note: this fact lives only in the chat. A new session later in the day would count the snack slot as open again.

---

## Turn 5 · 12:45 · "What should I eat for lunch?"

**Read**: Day node, `nodes/goals/Goals.md`, `nodes/pantry/Pantry.md`, `routines/rebalance.md`, `nodes/food/Chicken meatballs Spar.md`, `nodes/food/Rice.md`.

**Wrote**: nothing.

**Said**:
> **Lunch** (pantry only):
> - [[Chicken meatballs Spar]], 6 meatballs = 180 g — 324 kcal · 34 P · 18 F · 5 C (expires tomorrow)
> - [[Rice]], 250 g — 325 kcal · 7 P · 1 F · 70 C
> Lunch total: 649 kcal · 41 P · 19 F · 75 C.
> Dinner then needs about 55 g protein and 1180 kcal.

Note: the rules say "protein first" and "next slot in full", but not how much of the remaining protein lunch should take. The agent split it roughly in half. The meatballs are still `reviewed: false`; the suggestion did not say so.

---

## Turn 6 · 13:30 · "Had that, but only 4 meatballs."

**Read**: Day node, the two Food nodes, `nodes/goals/Goals.md`, `routines/log.md`.

**Wrote**: Day node, `## Lunch` with two lines (meatballs 120 g, rice 250 g), totals 1213 · 69 · 33 · 158.

Commit: `log: 2026-09-15 lunch Chicken meatballs Spar 120 g, Rice 250 g`

**Said**:
> Logged lunch: Chicken meatballs Spar 120 g — 216 kcal · 23 P · 12 F · 4 C; Rice 250 g — 325 kcal · 7 P · 1 F · 70 C. Left today: ~1287 kcal · 66 P · 27 F · 197 C. Dinner is the last open slot.

Note: "had that" made the agent take the rice amount from its own suggestion. The Pantry still says 450 g meatballs; logging never changes the Pantry.

---

## Turn 7 · 19:30 · "Dinner: 300 g skyr with 100 g blueberries and 40 g oats."

**Read**: Day node, three Food nodes, `nodes/goals/Goals.md`, `routines/log.md`.

**Wrote**: Day node, `## Dinner` with three lines, totals 1608 · 108 · 37 · 208.

Commit: `log: 2026-09-15 dinner Skyr 300 g, Blueberries 100 g, Oats 40 g`

**Said**:
> Logged dinner: Skyr 300 g, Blueberries 100 g, Oats 40 g — 395 kcal · 39 P · 4 F · 50 C. Left today: ~892 kcal · 27 P · 23 F · 147 C. No open slots left.

---

## Turn 8 · 21:00 · "Close the day."

**Read**: Day node, `nodes/goals/Goals.md`, the Food nodes eaten today (for `reviewed`), `routines/close-day.md`.

**Wrote**:
- Day node: `status: closed`, `## Summary` (slot table, goal line, four under/over bullets, verdict, one hint).
- `state.md`: `open_day: ""`.

Commit: `close-day: 2026-09-15 off target: calories low, protein low, fat low, carbs low`

**Said**:
> | Slot | kcal | Protein | Fat | Carbs |
> | --- | ---: | ---: | ---: | ---: |
> | Breakfast | ~672 | ~39 g | ~20 g | ~84 g |
> | Lunch | 541 | 30 g | 13 g | 74 g |
> | Dinner | 395 | 39 g | 4 g | 50 g |
> | **TOTAL** | **~1608** | **~108 g** | **~37 g** | **~208 g** |
>
> Goal: 2500 kcal · 135 g protein · 60 g fat · 355 g carbs.
> Calories 892 under · Protein 27 under · Fat 23 under · Carbs 147 under.
> **off target: calories low, protein low, fat low, carbs low**
> No snack and a small dinner left every macro low. Tomorrow keep the snack and add a grain at dinner.
> Unreviewed today: Chicken meatballs Spar, Croissant. Say ok to review.

---

## What I noticed while playing the agent

1. **"Plan today" gives one slot in full and rough lines for the rest.** The rebalance rules say so. It may feel thin for a morning plan.
2. **A removed slot has no home.** "No snack today" is chat-only. A fresh session forgets it.
3. **Clock slots can surprise.** A 10:15 croissant lands under Breakfast.
4. **The estimate mark spreads fast.** One guessed 60 g put `~` on every total of the day, including the close table.
5. **Two rules disagree about `state.md`.** The layout ticket's example lists unreviewed Foods under `## Open items`. The estimation policy says nothing about unreviewed Foods goes into `state.md`. I followed the estimation policy, so `## Open items` stayed empty all day.
6. **The suggestion does not say a Food is unreviewed.** Only the close line does.
7. **How much protein per slot?** The rules say protein first but not how to split the remaining protein between lunch and dinner.
8. **Rice means cooked rice here.** The node says so in `## Notes`, but the name does not.
9. **Reads per turn were small.** A log turn read state, index, one or two nodes, Goals and one routine. Under ten files every time.
