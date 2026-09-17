# food-planner-nutrition

A graph-engineered markdown vault that lets an agent act as a day-to-day food planner and nutrition tracker.

Planning happens on the wayfinder map: https://github.com/erodriguezh/food-planner-nutrition/issues/1

The spec is issue #22: https://github.com/erodriguezh/food-planner-nutrition/issues/22. The spec documents derived from it live in `docs/spec/`: [layout](docs/spec/layout.md), [nodes](docs/spec/nodes.md), [routines](docs/spec/routines.md), [context-mcp](docs/spec/context-mcp.md). The glossary is `CONTEXT.md`.

Research findings live in `docs/research/`.

## Use

Open the repository in Claude Code, a Claude Code cloud session, claude.ai or ChatGPT. The agent reads `ROUTER.md` first, then `index.md` and `state.md`, and picks a routine from `routines/` by the meaning of what you say.

## Lint

```
python3 lint/vault_lint.py
python3 -m unittest discover lint
python3 -m unittest discover acceptance
```

The first command checks the vault against the node schemas in `docs/spec/` and the Router, the Context MCP wiring (the skill file and its one Router pointer), `AGENTS.md`, Index, State and routine rules. The second runs the lint's own tests, the spec-document tests included. The third runs the tests of the acceptance script.

To run all three before every commit, install the local hook once:

```
git config core.hooksPath .githooks
```

The GitHub Action `.github/workflows/lint.yml` runs the same three steps on every push to `main` and fails the check on a violation.

## Acceptance run

```
python3 acceptance/seeded_day.py
```

Replays the seeded day of the prototype against the vault on a throwaway branch: ten turns, one commit per routine step, the files asserted after every turn, the lint after every commit. The branch is deleted at the end; pass `--keep` to inspect it, `--date <Monday>` to pick the week and `--repo <path>` to run on another clone.

The run tests the implementation on the current HEAD, the Router, the routines and the lint, and it writes its own seed fixture on the throwaway branch first, as one setup commit `acceptance: seed fixture` outside the ten turns. The Goals, the Pantry, the nodes, `index.md` and `state.md` the scenario needs come from that fixture, not from your live vault. So your own Days, your Goals changes and your new Foods never make the run fail, and the run never changes them.
