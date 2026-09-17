# Spec: layout

The files of the vault, what each one is for, and how the vault is checked.
Derived from the spec issue
([#22](https://github.com/erodriguezh/food-planner-nutrition/issues/22)) and
assembled by ticket [#28](https://github.com/erodriguezh/food-planner-nutrition/issues/28)
from the tickets that built each part. Every rule here is checked against the
files on `main` by `lint/test_spec_layout_routines.py`. The agent never loads
this document in daily use.

The other spec documents: [nodes](nodes.md) for the node schemas,
[routines](routines.md) for the eight routines, [context-mcp](context-mcp.md)
for the retrieval contract.

## Root

| File | Purpose |
| --- | --- |
| `ROUTER.md` | The one file the agent reads first. Pointers and hard rules, under 500 tokens. |
| `AGENTS.md` | One line, `Read ROUTER.md first.`, so every app starts the same way. |
| `CLAUDE.md` | A symlink to `AGENTS.md`. |
| `CONTEXT.md` | The glossary: one meaning per term, used in nodes, routines, the Index and chat. |
| `index.md` | The Index: one line per Food, Meal, Goals and Pantry node, one line per Day month. |
| `state.md` | The State: the open Day and the open items. Rewritten at the end of every routine that changes it. |
| `SKILL.md` | The one skill file with the Context MCP rule and its fallback. |
| `README.md` | Where the map, the spec issue, the spec documents and the check commands are. |

No templates folder. Schemas live in the spec documents and the routines. The
Obsidian config folder stays out of git (`.gitignore`).

## Folders

| Folder | Content |
| --- | --- |
| `nodes/food/` | One file per Food, flat. |
| `nodes/meal/` | One file per Meal, flat. |
| `nodes/goals/Goals.md` | The one Goals node. |
| `nodes/pantry/Pantry.md` | The one Pantry node. |
| `nodes/day/<YYYY-MM>/` | One folder per month, one Day file per date. Created at the first log of a month. |
| `routines/` | The eight routine files, named by lowercase verb: `log`, `rebalance`, `close-day`, `create-food`, `create-meal`, `pantry`, `goals`, `review`. |
| `docs/research/` | Research findings, one file per research ticket. |
| `docs/spec/` | The four spec documents. Build-time only. |
| `lint/` | The vault lint `lint/vault_lint.py` and its tests. |
| `acceptance/` | The seeded-day acceptance run `acceptance/seeded_day.py` and its tests. |
| `.githooks/` | The local pre-commit hook `.githooks/pre-commit`. |
| `.github/workflows/` | The GitHub Action `.github/workflows/lint.yml`. |

## Router

`ROUTER.md` is under 500 tokens (characters divided by four, the estimate the
lint applies). Its order: one line on what the vault is; the start rule; the
folder pointers; one line per routine ("When the user ... read `routines/x.md`");
the hard rules. No schema detail. Exactly one line points to `SKILL.md`, the
Context MCP pointer of the start rule; otherwise the session reads `index.md`,
then `state.md`.

The six hard rules, as written on `main`:

1. Grams only. Convert servings and ml before you write.
2. Links use the canonical name. Aliases are never link targets.
3. Plans are never stored. They live in the chat.
4. A new Food is written at once with `reviewed: false`. Ask nothing.
5. Write `index.md` and `state.md` after every change. Read fresh before you write; if the write fails, read again and redo.
6. One commit per routine step: `<routine>: <one line>`.

## App start

Four apps behave the same: Claude Code local, Claude Code cloud sessions,
claude.ai chat and ChatGPT chat. `AGENTS.md`, `CLAUDE.md` and the chat-app
project instructions hold the one line `Read ROUTER.md first.` and nothing
else. The lint fails an `AGENTS.md` with any other content.

A session reads `ROUTER.md`, then `index.md` (or calls `build_context` when
the Context MCP is connected, see [context-mcp](context-mcp.md)), then
`state.md`. Reads per turn stay under ten files.

## Common node conventions

Flat YAML frontmatter with core Obsidian types only (text, list, number,
checkbox, date). Every node has `type` and `name`; `name` equals the file base
name; base names are unique across the vault. Wikilinks in properties are
quoted strings and use canonical names. Amounts are grams. Column order
everywhere is kcal, protein, fat, carbs. The schemas are in [nodes](nodes.md).

## Index

The agent writes `index.md` at the same time as the node; no automation edits
it. It has one `##` section per node type in this order: `Food`, `Meal`, `Day`,
`Goals`, `Pantry`. Line shapes:

- Food: `- [[Name]] | <category> | <aliases plus label name, comma separated>`
- Meal: `- [[Name]] | <slots, comma separated, or any> | <aliases, comma separated>`
- Day: one line per month, `- <YYYY-MM> | nodes/day/<YYYY-MM>/`
- Goals and Pantry: the link only, `- [[Goals]]` and `- [[Pantry]]`

No free sentence; the aliases are the sentence. The Food and Meal lines form
the shared alias table. The lint fails a line without a node, a node without a
line, a wrong category or slot field, a missing or extra alias, and a month
folder without its line.

## State

```
---
type: state
open_day: "[[2026-09-14]]"
updated: 2026-09-14
---

## Open items
```

`open_day` is the quoted link of the one Day with `status: open`, or `""` when
none is open. `updated` is the day of the last change. The one body section
`## Open items` holds small pending things such as a Meal without cooked
weight; never a plan, never an unreviewed Food. The lint fails two open Days,
an `open_day` that names a Day that is not open, and an Open items line that
mentions review or links to a Food.

## Write path

Every write lands on `main`, one commit per routine step named
`<routine>: <one line>`, for example `log: 2026-09-14 breakfast Usual breakfast 1 portion`.
All files of one step go in one commit. Claude Code edits files with git and
pushes to `main`. Cloud sessions push their session branch, then create and
merge their own pull request. claude.ai writes through GitHub's remote MCP
server; ChatGPT writes with its built-in GitHub connector and falls back to the
remote MCP server. There is no lock between sessions: the Router rule "read
fresh before you write, redo on failure" covers it.

## Checks

Three commands, run in this order by the pre-commit hook and by the GitHub Action:

```
python3 -m unittest discover lint
python3 -m unittest discover acceptance
python3 lint/vault_lint.py
```

The first runs the lint's own tests, the spec-document tests included. The
second runs the tests of the acceptance script, one full seeded-day run on a
throwaway clone among them. The third is the vault lint: every node, the
Index, the State, the Router, the skill wiring, `AGENTS.md` and the routines
against the schemas, no model involved, exit code 1 on the first violation.

The hook `.githooks/pre-commit` runs them before every local commit once
installed with `git config core.hooksPath .githooks`. The GitHub Action
`.github/workflows/lint.yml` runs the same three steps on every push to
`main` and fails the check on a violation. The acceptance script's tests run
there too; that one full run happens on a temporary clone inside the job, so
no acceptance branch reaches the repository.

The three commands do not depend on the live mutable data of the vault. The
acceptance run builds its own canonical fixture on its throwaway branch, so a
real open Day, a Goals change or a new Food in the working tree the hook is
about to commit cannot fail the checks. Only the vault lint judges the live
data, and it judges it against the schemas.

## Acceptance run

```
python3 acceptance/seeded_day.py
python3 acceptance/seeded_day.py --date 2026-09-14 --keep
python3 acceptance/seeded_day.py --repo /path/to/another/clone
```

The seeded-day acceptance run repeats the prototype conversation against the
vault on the current HEAD, on a throwaway branch `acceptance/seeded-day-<stamp>`
in its own git worktree. A scripted stand-in plays the agent with the routine
files, the alias table and the rounding rule; there is no model in the loop.
Ten turns: plan today, the usual breakfast by alias, an unknown Food created
and logged with a guessed amount, "no snack today", a lunch suggestion, lunch
with a changed amount, dinner in servings, close the day, the next day's
breakfast, the weekly review. After every turn the script asserts the files
(Day lines and totals, the `~` on the guessed line and on the Day, the new Food
unreviewed with its Index line, the State open day, the Summary verdict words,
the commit subjects, the fixed review lines) and checks that the turn read
fewer than ten files. The lint gate sits in the commit wrapper
`Session.commit()`: every routine step commits, the lint reads that committed
tree, and a lint error stops the run before the next step, so the lint is green
after every commit and not only after every turn. Its sibling
`Session.commit_setup()` carries the same gate for the one setup commit of the
seed fixture below, and no other code path of the run commits. The branch and worktree are
removed at the end unless `--keep` is given; nothing is pushed and `main` never
moves. The turn-to-routine map is in [routines](routines.md).

The seed fixture against the mutable live vault: the run tests the
implementation on HEAD, the Router, the routines, the lint, the spec and the
script, but never the live mutable data. Before turn 1 the run writes the
seed fixture `FIXTURE` of `acceptance/seeded_day.py` on the throwaway branch and
lands it as one setup commit `acceptance: seed fixture`, outside the ten turns
and outside the seven `<routine>: <one line>` commits, with the same lint on
its committed tree. The fixture removes the whole `nodes/` tree and writes the
Goals with their 5 % bounds, the Pantry, `Usual breakfast` with its ingredient
Foods, Chicken breast, Rice, Eggs, `index.md` and a `state.md` with no open
Day, so every number the fixed lines and totals assume comes from the fixture.
The fixture is Python text and not a `seed/` folder of markdown, because the
lint fails node frontmatter outside `nodes/`. The preconditions of the run
therefore ask only for the implementation and a lint-green start state. A
valid change in the live vault, a real open Day, a Goals change, a Croissant
that became a real Food or a seeded date already logged, never stops the run
and never moves a number; the run is never skipped for such a state either.

## Repository

The spec issue says the repository goes private. On `main` today the repository
is public: GitHub Actions minutes are free for a public repository, which is
what lets the Action run. Making it private is an owner call recorded here, not
a build step.
