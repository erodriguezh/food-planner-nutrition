# Research: remote MCP on Cloudflare with GitHub-triggered index rebuild

Ticket: https://github.com/erodriguezh/food-planner-nutrition/issues/14
Date: 2026-09-10
Sources: primary only (Cloudflare docs, Anthropic/Claude docs, OpenAI docs, GitHub docs, MCP spec). Every claim has a URL. Items I could not verify are in the "Unverified" list.

## Summary

- Host the Context MCP as one stateless Cloudflare Worker. Use `createMcpHandler` from the `agents` SDK on the Streamable HTTP transport at `/mcp`. Cloudflare marks `McpAgent` and SSE as deprecated for new servers. No Durable Object is needed. [CF-1][CF-2][CF-4]
- Expose one tool, `build_context`. Load `graph-index.json` once per request from Workers KV, parse it, score it, and return the evidence packet. A few hundred KB fits well under the KV value limit of 25 MiB. [CF-6]
- Trigger the rebuild from a GitHub Actions workflow on `push` to `main`. The workflow builds `graph-index.json` and writes it to KV with `wrangler kv key put --path --remote`. This keeps the parser in the repo, avoids a webhook endpoint, and gives free minutes on a public repo (2,000 min/month on a private repo, Free plan). [CF-13][GH-5]
- A GitHub webhook to the Worker is the fallback. It needs HMAC validation of `X-Hub-Signature-256`, a 2XX reply within 10 seconds, and the Worker must then fetch every changed note through the GitHub API. [GH-1][GH-3]
- Auth: start with no auth. The MCP spec makes authorization OPTIONAL. Claude (web, desktop) lets you add a server URL and OAuth is optional. Claude Code accepts HTTP servers with no auth. ChatGPT reads the MCP auth spec; anonymous read-only servers are permitted. Add OAuth later with `@cloudflare/workers-oauth-provider` if the vault becomes private. [MCP-2][AN-1][AN-4][OA-3][CF-3]
- Client gating: Claude custom connectors work on Free, Pro, Max, Team, Enterprise (Free: one connector; mobile in beta). Claude Code needs Pro, Max, Team, Enterprise, or Console. ChatGPT needs developer mode; help-center pages state Plus, Pro, Business, Enterprise, Edu on web, but I could not fetch those pages directly (see Unverified). [AN-1][AN-2][AN-5][OA-4]
- Cost: the Worker fits in the Workers Paid included quota (10 M requests, 30 M CPU ms per month). KV reads fit in 10 M/month. One KV write per push fits in 1 M/month. Expected extra cost: USD 0 above the existing USD 5/month plan. [CF-5]

## Client compatibility table

| Client | Streamable HTTP | HTTP+SSE (legacy) | No auth | OAuth | Plan requirement | Source |
|---|---|---|---|---|---|---|
| claude.ai web | Yes (implied: docs point to MCP inspector with "SSE" or "Streamable HTTP") | Yes (same) | Yes. "Optionally, click 'Advanced settings' to specify an OAuth Client ID and OAuth Client Secret." | Yes, optional client ID/secret | "Free, Pro, Max, Team, and Enterprise plans." "Free users are limited to one custom connector." | [AN-1][AN-2] |
| Claude Desktop | Same as web (connectors "are configured and brokered through your Claude account") | Same | Same | Same | Same as web | [AN-1][AN-2] |
| Claude mobile (iOS, Android) | Same server, but "Installing connectors on mobile is currently in beta—Claude Desktop and web remain the primary path for custom connectors." | Same | Same | Same | Same as web; install path in beta | [AN-2] |
| Claude Code | Yes. `claude mcp add --transport http <name> <url>`. "HTTP is the recommended transport." | Yes, deprecated. "The SSE (Server-Sent Events) transport is deprecated. Use HTTP servers instead." Auto-fallback from HTTP to SSE needs v2.1.265+. | Yes (URL only) or `--header "Authorization: Bearer ..."` | Yes. `/mcp` or `claude mcp login <name>` | "Claude Code requires a Pro, Max, Team, Enterprise, or Console account. The free Claude.ai plan does not include Claude Code access." | [AN-4][AN-5] |
| ChatGPT web | Yes. "A public endpoint supports streamable HTTP, typically at `/mcp`." | The older API-MCP guide says the dev URL must end with `/sse/`; treat SSE as legacy | Permitted for read-only: "Many plugin MCP servers can operate in a read-only, anonymous mode, but anything that exposes customer-specific data or write actions should authenticate users." | OAuth 2.1 per MCP spec; CIMD preferred, DCR supported | Developer mode. "Developer mode availability can depend on account and workspace policy." Help center (search snippet only): "Developer mode is available to Pro, Plus, Business, Enterprise, and Education accounts on the web." | [OA-1][OA-2][OA-3][OA-4] |
| ChatGPT desktop | Not stated in primary docs I could fetch | Not stated | Not stated | Not stated | Help-center snippet says "on the web" | [OA-4] (Unverified) |

Notes:
- The MCP spec 2025-06-18 defines two standard transports: stdio and Streamable HTTP. Streamable HTTP "replaces the HTTP+SSE transport from protocol version 2024-11-05." Servers that want old clients "Continue to host both the SSE and POST endpoints of the old transport, alongside the new 'MCP endpoint'." [MCP-1]
- The spec says "Authorization is OPTIONAL for MCP implementations." When you add auth, the server "MUST implement OAuth 2.0 Protected Resource Metadata (RFC9728)" and clients "SHOULD support the OAuth 2.0 Dynamic Client Registration Protocol (RFC7591)". [MCP-2]
- Claude connects "from Anthropic's cloud infrastructure, rather than from your local device", so the Worker URL must be public. [AN-1]

## Hosting on Cloudflare Workers

| Item | Finding | Source |
|---|---|---|
| Template | `npm create cloudflare@latest` with `cloudflare/ai/demos/remote-mcp-authless` (no auth) or `cloudflare/ai/demos/remote-mcp-github-oauth`. Warning on the page: "The quick-deploy templates in this section still use the deprecated `McpAgent` path. Do not use that path for a new server." "Use `createMcpHandler` for a new stateless server." | [CF-1] |
| Transport | "New servers should use the stateless Streamable HTTP handler." SSE "has been deprecated in favor of Streamable HTTP." Endpoint served at `/mcp`. | [CF-2] |
| Handler API | `import { createMcpHandler } from "agents/mcp/server"`; `createMcpHandler(factory, options?)`; register tools with `server.registerTool(name, { description, inputSchema }, handler)`. No Durable Object needed. "Store cross-request data behind an authenticated handle in a Durable Object, D1, KV, or R2". | [CF-4] |
| McpAgent status | "deprecated and feature-frozen"; each instance "backed by a Durable Object". "Migrate to createMcpHandler at your earliest convenience." | [CF-4b] |
| Auth options | No auth (authless template); `@cloudflare/workers-oauth-provider` with self-handled OAuth, a third-party provider (GitHub, Google), a BYO provider (Auth0, Stytch, WorkOS, Descope), or Cloudflare Access. "The MCP Server (your Worker) generates and issues its own token to the MCP client." | [CF-3] |
| Runtime limits (Paid) | CPU time default 30 s (max 5 min); 128 MB memory per isolate; 10,000 subrequests per request; 64 MiB uncompressed script size. The scorer runs in a few ms on a few-hundred-KB index. | [CF-7] |

Recommended shape of the Worker:

1. `GET /health` returns the index version (KV key `graph-index:meta`).
2. `POST/GET/DELETE /mcp` handled by `createMcpHandler`. The factory registers `build_context(question: string)`.
3. The tool loads `graph-index.json` from KV with `env.INDEX.get("graph-index", { type: "json", cacheTtl: 300 })`, scores nodes deterministically, follows at most one edge, and returns the evidence packet as `content: [{ type: "text", text }]`.
4. Optional `POST /rebuild` webhook route (see option B) with HMAC validation.

## Rebuild-trigger options

| Option | How it works | Pros | Cons | Sources |
|---|---|---|---|---|
| A. GitHub Action writes KV (recommended) | Workflow `on: push: branches: [main]`. Steps: checkout, run the index builder, `npx wrangler kv key put graph-index --path graph-index.json --namespace-id <id> --remote`. Secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`. | Builder has the full checkout, so no GitHub API calls. Deterministic. No public endpoint to protect. Free minutes for public repos; 2,000 min/month for private repos on Free. Index is visible in KV within about 60 s. | Needs a Cloudflare API token in GitHub secrets. Adds a 1-2 min delay per push. | [CF-12][CF-13][CF-14][CF-15][GH-5] |
| A2. GitHub Action commits `graph-index.json` | Same workflow, then `git commit` the file back to the repo; Worker fetches the raw file. | Index is versioned in git, easy to diff. | Every push causes a second push. Worker fetch of raw content per request costs a subrequest and depends on GitHub availability; unauthenticated REST calls are limited to 60/hour. Contents API supports files up to 1 MB with all features, 1-100 MB only with raw media type. | [GH-6][GH-7] |
| A3. GitHub Action uploads to R2 | `npx wrangler r2 object put <bucket>/graph-index.json --file graph-index.json --remote`. | R2 has 10 GB-month, 1 M Class A, 10 M Class B free per month; zero egress. | Class B read per tool call unless cached. No edge cache by default; KV caches hot keys at the edge. | [CF-9][CF-16] |
| B. GitHub webhook to Worker | Repo webhook, event `push`, content type `application/json`, secret. Worker validates `X-Hub-Signature-256` (HMAC SHA-256, constant-time compare), replies 2XX within 10 s, then fetches changed files (`commits[].added/removed/modified`) via the GitHub API and writes KV. | No CI minutes. Fast (seconds). | Worker must clone or fetch notes through the GitHub REST API (rate limits: 60/h unauthenticated, 5,000/h with a token). Payload lists at most 2048 commits and is capped at 25 MB; a large push forces a full rebuild. Needs async processing (Queues or `waitUntil`) to stay under 10 s. Same-key KV writes are limited to 1 per second. | [GH-1][GH-2][GH-3][GH-4][GH-7][CF-17] |
| C. Cloudflare Workers Builds | Connect the repo in the dashboard; "automated builds and deployments for your Worker on push." Build the index in the build command and ship it as a static asset or embedded module. | No GitHub secrets needed; 6,000 build min/month on Paid then USD 0.005/min. | Couples index rebuild to a Worker redeploy. Worker name must match `name` in wrangler config. | [CF-18][CF-19] |

Recommendation: option A. It is the simplest deterministic path and it needs no public write endpoint.

## Storage options for a few-hundred-KB index

| Store | Fit | Limits | Cost inside Workers Paid | Source |
|---|---|---|---|---|
| Workers KV (recommended) | Best. One key, read on every tool call. Edge-cached: "Frequent reads from the same location return the cached value." | Value max 25 MiB. Same-key writes max 1/s. Eventual: "Changes may take up to 60 seconds or more to be visible in other global network locations." | 10 M reads, 1 M writes, 1 GB storage included; then USD 0.50/M reads, USD 5.00/M writes, USD 0.50/GB-month. | [CF-5][CF-6][CF-8][CF-17] |
| R2 | Good. Strongly consistent object. | Object put via binding or wrangler. | Free tier 10 GB-month, 1 M Class A, 10 M Class B per month; zero egress. | [CF-9][CF-16] |
| D1 | Over-engineered for one JSON blob; useful only if you later query nodes by SQL. | Row-based billing. | 25 B rows read, 50 M rows written, 5 GB included. | [CF-10] |
| Repo raw URL / Contents API | Works, but adds an external dependency per request. | Contents API: 1 MB full features; 1-100 MB raw media type only. Unauthenticated REST: 60 requests/hour. | No Cloudflare cost; one subrequest per call. | [GH-6][GH-7] |
| Static asset in the Worker | Possible: rebuild triggers a redeploy; asset requests are "free and unlimited". | Needs a deploy per push (option C). | Free. | [CF-20] |
| Durable Object | Not needed; `McpAgent` is deprecated. | - | 1 M requests, 400,000 GB-s included on Paid. | [CF-4b][CF-11] |

## Cost notes (Workers Paid, USD)

- Workers Paid: USD 5/month base. Included: 10 M requests/month, 30 M CPU ms/month. Overage: USD 0.30 per extra 1 M requests, USD 0.02 per extra 1 M CPU ms. [CF-5]
- Workers KV: included 10 M reads, 1 M writes, 1 M deletes, 1 M list, 1 GB. Overage: USD 0.50/M reads, USD 5.00/M writes. [CF-8]
- R2: 10 GB-month, 1 M Class A, 10 M Class B free; USD 0.015/GB-month, USD 4.50/M Class A, USD 0.36/M Class B; egress free. [CF-9]
- D1: 25 B rows read, 50 M rows written, 5 GB included; USD 0.001/M rows read, USD 1.00/M rows written, USD 0.75/GB-month. [CF-10]
- Durable Objects: 1 M requests, 400,000 GB-s, 5 GB-month (SQLite) included; USD 0.15/M requests, USD 12.50/M GB-s. Not needed for the recommended design. [CF-11]
- Workers Builds (option C only): 6,000 build minutes/month on Paid, then USD 0.005/minute. [CF-19]
- GitHub Actions: free for public repos on standard runners; 2,000 minutes/month for private repos on Free, 3,000 on Pro. [GH-5]
- Estimate for this project: a personal vault with under 10,000 tool calls and under 500 pushes per month stays at USD 0 above the existing USD 5 plan.

## Unverified

1. ChatGPT plan gating for custom MCP connectors. The OpenAI help-center pages (articles 12584461 and 11487775) return HTTP 403 to automated fetches. The sentence "Developer mode is available to Pro, Plus, Business, Enterprise, and Education accounts on the web" comes from a search-engine snippet of article 12584461, not from a direct read. Confirm in a browser. [OA-4]
2. ChatGPT desktop and mobile support for custom MCP connectors. The developer docs I fetched mention ChatGPT settings on the web only. Not confirmed.
3. Whether claude.ai still accepts the legacy HTTP+SSE transport for new custom connectors. The current help article does not name a transport. The MCP inspector step in the older article offered "SSE" or "Streamable HTTP" (search snippet). The article "Building Custom Connectors via Remote MCP Servers" (11503834) now returns 404.
4. Claude mobile custom connector install flow. The help center says it is "in beta" with no further detail. [AN-2]
5. Rate limits and caching for `raw.githubusercontent.com`. GitHub docs I fetched cover the REST Contents API, not the raw host. Treat raw-host limits as undocumented.
6. Billing of `env.ASSETS.fetch()` calls made from inside a Worker. The static-assets billing page does not address this case. [CF-20]
7. KV `cacheTtl` interaction with a 25 MiB value. KV docs give the 60 s default and recommend raising it; no size-specific note. [CF-8]
8. Exact behavior of Claude Code's HTTP-to-SSE automatic switch below v2.1.265. The doc states the version floor only. [AN-4]

## Sources

Cloudflare
- [CF-1] Build a remote MCP server: https://developers.cloudflare.com/agents/guides/remote-mcp-server/
- [CF-2] MCP transport: https://developers.cloudflare.com/agents/model-context-protocol/transport/
- [CF-3] MCP authorization: https://developers.cloudflare.com/agents/model-context-protocol/authorization/
- [CF-4] createMcpHandler API: https://developers.cloudflare.com/agents/model-context-protocol/apis/handler-api/
- [CF-4b] McpAgent API (deprecated): https://developers.cloudflare.com/agents/model-context-protocol/mcp-agent-api/
- [CF-5] Workers pricing: https://developers.cloudflare.com/workers/platform/pricing/
- [CF-6] KV limits: https://developers.cloudflare.com/kv/platform/limits/
- [CF-7] Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- [CF-8] KV pricing: https://developers.cloudflare.com/kv/platform/pricing/ and How KV works: https://developers.cloudflare.com/kv/concepts/how-kv-works/
- [CF-9] R2 pricing: https://developers.cloudflare.com/r2/pricing/
- [CF-10] D1 pricing: https://developers.cloudflare.com/d1/platform/pricing/
- [CF-11] Durable Objects pricing: https://developers.cloudflare.com/durable-objects/platform/pricing/
- [CF-12] Deploy with GitHub Actions: https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/
- [CF-13] Wrangler KV commands (`kv key put --path --remote`): https://developers.cloudflare.com/kv/reference/kv-commands/
- [CF-14] Wrangler commands overview: https://developers.cloudflare.com/workers/wrangler/commands/
- [CF-15] KV write API (`put`, 1 write/s per key, bulk REST API): https://developers.cloudflare.com/kv/api/write-key-value-pairs/
- [CF-16] Wrangler R2 commands (`r2 object put --file --remote`): https://developers.cloudflare.com/r2/reference/wrangler-commands/ and R2 Workers API: https://developers.cloudflare.com/r2/api/workers/workers-api-reference/
- [CF-17] KV consistency and cacheTtl: https://developers.cloudflare.com/kv/concepts/how-kv-works/
- [CF-18] Workers Builds: https://developers.cloudflare.com/workers/ci-cd/builds/
- [CF-19] Workers Builds limits and pricing: https://developers.cloudflare.com/workers/ci-cd/builds/limits-and-pricing/
- [CF-20] Static assets billing: https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/ and Cache API: https://developers.cloudflare.com/workers/runtime-apis/cache/

Anthropic / Claude
- [AN-1] Get started with custom connectors using remote MCP: https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- [AN-2] Use connectors to extend Claude's capabilities: https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities
- [AN-3] Remote MCP servers (Claude API, not claude.ai): https://platform.claude.com/docs/en/agents-and-tools/remote-mcp-servers
- [AN-4] Claude Code MCP: https://code.claude.com/docs/en/mcp
- [AN-5] Claude Code setup (plan requirement): https://code.claude.com/docs/en/setup

OpenAI
- [OA-1] Connect and test your plugin (ChatGPT developer mode, `/mcp`, streamable HTTP): https://developers.openai.com/plugins/deploy/connect-chatgpt
- [OA-2] Building MCP servers for plugins and API integrations: https://developers.openai.com/api/docs/mcp
- [OA-3] Authentication patterns for plugin MCP servers: https://developers.openai.com/apps-sdk/build/auth
- [OA-4] Developer mode and MCP apps in ChatGPT (help center; fetch blocked, snippet only): https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- [OA-5] Responses API MCP tool (API, not ChatGPT): https://developers.openai.com/api/docs/guides/tools-connectors-mcp

GitHub
- [GH-1] Validating webhook deliveries: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- [GH-2] Webhook events and payloads (push): https://docs.github.com/en/webhooks/webhook-events-and-payloads
- [GH-3] Webhook best practices (10 s reply, async): https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks
- [GH-4] Creating webhooks: https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks
- [GH-5] About billing for GitHub Actions: https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions
- [GH-6] REST API repository contents (size tiers): https://docs.github.com/en/rest/repos/contents
- [GH-7] REST API rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api

MCP specification
- [MCP-1] Transports (2025-06-18): https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
- [MCP-2] Authorization (2025-06-18): https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization
