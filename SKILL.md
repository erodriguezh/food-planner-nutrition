---
name: context-mcp
description: How the agent uses the Context MCP for retrieval in this vault, and what it does without it.
---

# Context MCP

The Context MCP is a read-only retrieval service for this vault. It has one tool.

## Tool

`build_context(question)` takes the user's question as one string. No routine hint, no options.

It returns an evidence packet with five fields:

- `node`: the path of the best node.
- `section`: the heading of the best section, with its text.
- `linked`: one linked node with its path and frontmatter, or empty.
- `status`: `ok`, or `not_found` when no node fits.
- `index_version`: the commit hash the index was built from.

Later versions may add fields. They may never remove one of the five.

## Order

Two paths. A session takes one of them, never both.

1. Connected and the call returns `status: ok`: call `build_context(question)` first and use its evidence packet, then read `state.md`. Do not read `index.md`.
2. Not connected, or the fallback below: read `index.md`, then `state.md`, as the Router says.

The service is read-only. Every write goes through the routines.

## Fallback

When the server is down, the call fails, or it returns `not_found`, take path 2 — read `index.md`, then `state.md` — and say one short line:

"context server down or no files found, read files directly."

Then continue as if the service were not connected.
