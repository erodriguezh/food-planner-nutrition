# Router

Personal food planner and nutrition tracker for one person. Markdown vault, agent-operated.

## Start every session

1. Context MCP connected? Follow `SKILL.md`. Otherwise read `index.md`.
2. Read `state.md`.

## Where things are

- `nodes/food/`, `nodes/meal/`, `nodes/goals/Goals.md`, `nodes/pantry/Pantry.md`, `nodes/day/<YYYY-MM>/`
- `routines/` — how to do each job
- `state.md` — open day and open items
- `CONTEXT.md` — glossary

## Routines

- When the user ate something, changed or removed an entry: read `routines/log.md`
- When the user asks what is left or what to eat: read `routines/rebalance.md`
- When the user closes the day, or a log auto-closes one or refreshes a closed one: read `routines/close-day.md`
- When a food is new or a label photo arrives: read `routines/create-food.md`
- When the user names a meal: read `routines/create-meal.md`
- When the user bought, ran out of, or lists food: read `routines/pantry.md`
- When the user sets or changes targets: read `routines/goals.md`
- When the user says "review" or asks about the week: read `routines/review.md`

## Hard rules

1. Grams only. Convert servings and ml before you write.
2. Links use the canonical name. Aliases are never link targets.
3. Plans are never stored. They live in the chat.
4. A new Food is written at once with `reviewed: false`. Ask nothing.
5. Write `index.md` and `state.md` after every change. Read fresh before you write; if the write fails, read again and redo.
6. One commit per routine step: `<routine>: <one line>`.
