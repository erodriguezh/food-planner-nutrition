# Spec: Context MCP

Contract of the deterministic retrieval service. Derived from the spec issue
([#22](https://github.com/erodriguezh/food-planner-nutrition/issues/22)) and built by ticket
[#27](https://github.com/erodriguezh/food-planner-nutrition/issues/27).
The agent never loads this document in daily use; the skill file `SKILL.md` at the vault root carries the rule.
The vault lint (`python3 lint/vault_lint.py`) checks the wiring: the skill file exists, `ROUTER.md` points to it in one line, and no other markdown file of the vault repeats the line it quotes. The contract itself gets its test with the internals map, see Internals.

## Scope

This document fixes the contract only: the tool, the packet, the read-only rule, the index rebuild trigger, the fallback and the auth requirement. The vault starts without the service. With no MCP connected a session reads the Router, then the Index, then the State, as before.

## Tool

One tool: `build_context(question: string)`. No routine hint, no options. Retrieval is logic, not a model call.

## Evidence packet

| Field | Meaning |
| --- | --- |
| `node` | path of the best node |
| `section` | heading of the best section, with its text |
| `linked` | one linked node with path and frontmatter, or empty |
| `status` | `ok` or `not_found` |
| `index_version` | commit hash the index was built from |

The internals map may add fields and may never remove one of these five.

## Read-only

The service never writes to the vault. Every write goes through a routine and its write path. The service never sees an image; the model reads label photos itself.

## Index rebuild

The index of the service rebuilds on each push to `main`. It reads the Index for links and aliases and the node frontmatter for numbers.

## Rule and fallback

The rule for calling the service lives in one skill file, `SKILL.md`, plus one pointer line in `ROUTER.md`. No app configuration holds a copy; `AGENTS.md` and the chat-app project instructions hold only `Read ROUTER.md first.`

When the service is down or returns `not_found`, the agent reads the files directly and says one line:

"context server down or no files found, read files directly."

## Auth requirement

Auth must support many paying subscribers, each connecting their own private vault repository. The method and its build belong to the internals map.

## Internals

Scoring rules, section pick, index builder, hosting, auth build, subscription flow and the paid service are out of scope here. Their owner is the internals map, charted after the vault build:
[Task: chart the Context MCP internals map](https://github.com/erodriguezh/food-planner-nutrition/issues/19).

The contract gets no test in this spec. Its test seam is `build_context(question)` and belongs to the internals map.
