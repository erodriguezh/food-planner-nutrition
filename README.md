# food-planner-nutrition

A graph-engineered markdown vault that lets an agent act as a day-to-day food planner and nutrition tracker.

Planning happens on the wayfinder map: https://github.com/erodriguezh/food-planner-nutrition/issues/1

Research findings live in `docs/research/`.

## Use

Open the repository in Claude Code, a Claude Code cloud session, claude.ai or ChatGPT. The agent reads `ROUTER.md` first, then `index.md` and `state.md`, and picks a routine from `routines/` by the meaning of what you say.

## Lint

```
python3 lint/vault_lint.py
python3 -m unittest discover lint
```

The first command checks the vault against the node schemas in `docs/spec/` and the Router, the Context MCP wiring (the skill file and its one Router pointer), `AGENTS.md`, Index, State and routine rules. The second runs the lint's own tests.

To run both before every commit, install the local hook once:

```
git config core.hooksPath .githooks
```

There is no GitHub Action. The check runs locally only.
