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

The service may add fields. It may never remove one of the five.

## Order

1. Connected: call `build_context(question)` first, before any file read. Read `state.md` after it.
2. Not connected: read `index.md`, then `state.md`, as the Router says.

Treat the packet as evidence, not as an answer. Open a node only when the packet does not settle the question. The service never writes; every write goes through the routines.

## Fallback

When the call fails, times out, or returns `not_found`, read the files directly and say one short line:

"context server down or no files found, read files directly."

Then continue as if the service were not connected.
