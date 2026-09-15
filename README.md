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

The first command checks the vault against the schemas in `docs/spec/`. The second runs the lint's own tests. Both run in CI on every push to `main`.
