# Research: auth for a paid Context MCP

Ticket: https://github.com/erodriguezh/food-planner-nutrition/issues/18
Date: 2026-09-12
Sources: primary only (MCP spec, Anthropic/Claude docs, OpenAI docs, Cloudflare docs, Stripe docs, GitHub docs, vendor pricing pages). Every claim has a URL. Items I could not verify are in the "Unverified" list.
Builds on: [cloudflare-context-mcp.md](https://github.com/erodriguezh/food-planner-nutrition/blob/research/cloudflare-context-mcp/docs/research/cloudflare-context-mcp.md) (issue 14). This file does not repeat the transport, hosting, or index-rebuild findings.

## Summary

- The current MCP spec is 2026-07-28. It makes RFC 9728 Protected Resource Metadata a MUST for servers. It marks Dynamic Client Registration (RFC 7591) as deprecated and prefers Client ID Metadata Documents (CIMD). Client priority is: pre-registered credentials, then CIMD, then DCR, then ask the user. [MCP-1][MCP-2][MCP-3]
- All three clients support DCR and CIMD today. Claude (web, desktop, mobile, Claude Code) supports `oauth_dcr` and `oauth_cimd` "out of the box". ChatGPT prefers CIMD and also runs DCR. Both also accept a pre-registered client ID. So one authorization server that enables CIMD and DCR, and allows public clients (`token_endpoint_auth_method: "none"`), serves all three clients. [AN-1][AN-2][OA-1]
- Redirect URIs to allow: `https://claude.ai/api/mcp/auth_callback` (Claude web, desktop, mobile), `http://localhost:PORT/callback` and `http://127.0.0.1:PORT/callback` with any port (Claude Code), `https://chatgpt.com/connector_platform_oauth_redirect` (ChatGPT, when the server sends `iss`). [AN-1][AN-2][OA-1]
- On Cloudflare Workers, `@cloudflare/workers-oauth-provider` gives you a full OAuth 2.1 authorization server in the same Worker. It serves RFC 8414 and RFC 9728 metadata, DCR, CIMD (`clientIdMetadataDocumentEnabled: true` + `global_fetch_strictly_public`), PKCE S256, and hashed token storage in one KV namespace. It passes per-user `props` to `createMcpHandler` through `getMcpAuthContext()`. Cost: USD 0 above the Workers Paid plan. [CF-1][CF-2][CF-3]
- BYO providers (Auth0, Stytch, WorkOS, Descope, Clerk) all have free tiers that cover a small subscriber base, but they add a second system and a second login UI. Cloudflare Access does not fit: its docs describe manual OAuth client setup, not DCR or CIMD, and the free plan stops at 50 users. [CF-4][CF-5][BYO-1..5]
- Tie the plan to the login with Stripe: Checkout Session in `mode: 'subscription'` creates the customer and subscription. A webhook (`customer.subscription.*`, `invoice.paid`, `invoice.payment_failed`) updates one D1 row per subscriber. The `/authorize` handler denies token issue when `status` is not `active` or `trialing`. Each tool call also reads the same row, so a cancel takes effect on the next call. [ST-1][ST-2][ST-3]
- Store no GitHub secret per user. Each subscriber installs one GitHub App on their vault repo. Store only `installation_id` in D1. The Worker holds the app private key as one Worker secret and mints a 1-hour installation token when it needs the repo. Fine-grained PATs work but expire (30-day default) and must be stored encrypted per user. [GH-1][GH-2][GH-3][GH-6]
- Simplest path that works with all three clients: one Worker, `workers-oauth-provider` as the authorization server, one GitHub App as both the login provider and the repo access path, Stripe Checkout plus one webhook route, one D1 table. See "Recommended path".

## 1. How each client handles MCP OAuth today

| Client | RFC 9728 discovery | CIMD | DCR (RFC 7591) | Pre-registered client ID/secret | Redirect URI | Notes | Source |
|---|---|---|---|---|---|---|---|
| claude.ai web, Claude Desktop, Claude mobile, Cowork | Yes. Reads `WWW-Authenticate: Bearer resource_metadata=...` on a 401. Falls back to probing `/.well-known/oauth-protected-resource/<path>` then `/.well-known/oauth-protected-resource`. "The 401 status is required." | Yes, "Supported out of the box". Claude picks CIMD only when the AS metadata has both `client_id_metadata_document_supported: true` and `"none"` in `token_endpoint_auth_methods_supported`. Otherwise it falls back to DCR. | Yes, "Supported out of the box". Needs `registration_endpoint`. "DCR causes Claude to register a new client on every fresh connection." | Yes. Custom connector form has optional "OAuth Client ID" and "OAuth Client Secret" under "Advanced settings". "When a user adds a custom connector by URL, the OAuth Client Secret field is optional." | `https://claude.ai/api/mcp/auth_callback` | PKCE S256 on every request. Refresh tokens must rotate for public clients. Token endpoint must accept `application/x-www-form-urlencoded`. Discovery, register, and token endpoints must answer within 10 s. Egress IP range `160.79.104.0/21`. | [AN-1][AN-3] |
| Claude Code | Yes. "first checks RFC 9728 Protected Resource Metadata at `/.well-known/oauth-protected-resource`, then falls back to RFC 8414 authorization server metadata". `oauth.authServerMetadataUrl` can override. | Yes. "Claude Code also supports servers that use a Client ID Metadata Document (CIMD) instead of Dynamic Client Registration, and discovers these automatically." Its CIMD is at `https://claude.ai/oauth/claude-code-client-metadata`. | Yes. "Claude Code can automatically register a client and handle the OAuth flow without pre-configured credentials." | Yes. `claude mcp add --transport http --client-id <id> --client-secret --callback-port 8080 <name> <url>`, or `oauth.clientId` and `oauth.callbackPort` in `.mcp.json`. Secret goes to the keychain. | `http://localhost:PORT/callback`; the port is random unless `--callback-port` is set. The CIMD declares `http://localhost/callback` and `http://127.0.0.1/callback`; the AS "must accept both with the port component ignored". | Login with `/mcp` or `claude mcp login <name>` (v2.1.186+); `--no-browser` for SSH (v2.1.191+). Refresh on 401, one retry. `oauth.scopes` pins scopes. | [AN-2][AN-1] |
| ChatGPT (developer mode) | Yes. Server "must host metadata at `/.well-known/oauth-protected-resource`" and return 401 with `WWW-Authenticate`. AS must expose RFC 8414 or OIDC discovery with `code_challenge_methods_supported` that "must include `S256`". | Yes, preferred. "ChatGPT uses an HTTPS metadata document URL as its `client_id`." Token auth methods: `none` (PKCE) or `private_key_jwt`. Set `client_id_metadata_document_supported: true`. | Yes. "ChatGPT runs DCR once per MCP server connection, then keeps and reuses the registered OAuth client for that connection." | Yes. "Organizations can manually create OAuth clients for ChatGPT." | `https://chatgpt.com/connector_platform_oauth_redirect` when the AS supports issuer identification (RFC 9207 `iss`); otherwise `https://chatgpt.com/connector/oauth/{callback_id}`. "Copy the exact production redirect URI shown in the MCP server's management page." | Sends `resource=` on authorization and token requests; "copy that value into the access token (commonly the `aud` claim)". Token verification "sits with you, not with ChatGPT". Per-tool `securitySchemes` (`noauth` or `oauth2`). | [OA-1][OA-2] |

Spec notes (2026-07-28):

- "MCP servers MUST implement OAuth 2.0 Protected Resource Metadata (RFC9728)." "Authorization servers and MCP clients SHOULD support OAuth Client ID Metadata Documents." "Authorization servers and MCP clients MAY support ... Dynamic Client Registration ... Note that Dynamic Client Registration is deprecated." [MCP-1]
- Client priority order: "1. Use pre-registered client information ... 2. Use Client ID Metadata Documents if the Authorization Server indicates that it supports them ... 3. Use Dynamic Client Registration as a fallback ... 4. Prompt the user." [MCP-2]
- The AS "MUST validate redirect URIs presented in an authorization request against those in the metadata document." The client `client_id` URL must use https and have a path. [MCP-2]
- The `resource` parameter is a client MUST on both requests. Servers "MUST validate that access tokens were issued specifically for them as the intended audience". [MCP-1]
- New in 2026-07-28: the AS "SHOULD include the `iss` parameter in authorization responses" (RFC 9207); clients MUST validate it when present. Also: `application_type: "native"` is required for loopback DCR clients. [MCP-3]
- What this means for the server: enable CIMD and DCR together. Allow public clients. Set `authorization_response_iss_parameter_supported: true` if the library supports it. Then all three clients pick a working path without any manual client registration. [MCP-2][AN-1][OA-1]

## 2. Options on Cloudflare Workers

`McpAgent` is "deprecated and feature-frozen". Use `createMcpHandler` from `agents/mcp/server`. It works with `workers-oauth-provider`: "A compatible `@cloudflare/workers-oauth-provider` supplies verified standard `AuthInfo` to SDK v2 callbacks at `context.http.authInfo`", and `getMcpAuthContext()` returns the `props` set at `completeAuthorization()`. "Do not log or return `authInfo.token` or `authInfo.extra.props`." [CF-3][CF-6]

| Option | How it works | Pros | Cons | Cost | Sources |
|---|---|---|---|---|---|
| A. `@cloudflare/workers-oauth-provider`, self-handled (recommended) | `new OAuthProvider({ apiRoute: "/mcp", apiHandler, defaultHandler, authorizeEndpoint: "/authorize", tokenEndpoint: "/token", clientRegistrationEndpoint: "/register", clientIdMetadataDocumentEnabled: true })`. You write `/authorize`: `parseAuthRequest`, log the user in, then `completeAuthorization({ request, userId, scope, props })`. The library serves RFC 8414 metadata at `/.well-known/oauth-authorization-server` and RFC 9728 metadata at `/.well-known/oauth-protected-resource/{path}`. "Access tokens, refresh tokens, authorization codes, and client secrets are stored only by hash. `props` are encrypted with AES-GCM." PKCE S256 only. Audience: "a token for `https://mcp.example.com/mcp` is accepted at `/mcp/tools`". | One Worker, one KV namespace (`OAUTH_KV`). CIMD and DCR in one switch. Public clients allowed by default, which Claude's CIMD needs. Props carry `userId` and `installationId` to every tool call. Cloudflare's own doc lists this as the first option. | You own the login page and the consent page. You must write the "who is this user" step yourself (option B does that with GitHub). "Do not automatically approve a request in production." | USD 0 above Workers Paid. KV reads and writes for tokens stay far below the 10 M read and 1 M write included quota for a small subscriber base. | [CF-1][CF-2][CF-4] |
| B. GitHub as the login provider (inside option A) | Same library. The `defaultHandler` redirects the user to GitHub, gets the GitHub user back, then calls `completeAuthorization`. Cloudflare ships `cloudflare/ai/demos/remote-mcp-github-oauth`: the Worker "acts as OAuth Server to your MCP clients" and "as OAuth Client to your real OAuth server (in this case, GitHub)". Needs `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `COOKIE_ENCRYPTION_KEY`, KV `OAUTH_KV`. GitHub callback is `/callback` on the Worker. | Subscribers already have GitHub accounts, because the vault is a GitHub repo. No password store. The GitHub user id is the natural subscriber key. The same GitHub App can also give repo access (section 3). | The demo template still uses the deprecated `McpAgent` path; port the handler to `createMcpHandler`. Users must have a GitHub account. | USD 0. GitHub OAuth is free. | [CF-1][CF-4][CF-7] |
| C. BYO provider: Auth0 | Cloudflare doc: "Email, social logins, enterprise SSO with token refresh". Auth0 becomes the AS in `authorization_servers`. | Hosted login, MFA, social login. | Second vendor. Second dashboard. DCR and MCP settings on Auth0 not verified from primary docs (see Unverified 5). | Free up to 25,000 MAU, 1 custom domain. Essentials "from $35/month" at 500 MAU. | [CF-4][BYO-1] |
| D. BYO provider: Stytch | Cloudflare doc: "Email, Google login, enterprise SSO". Stytch Connected Apps act as the AS; supports DCR; example "can also be deployed as a Cloudflare Worker". | Made for MCP; RBAC on tool calls. | Second vendor. CIMD support not stated on the page I read. | Free up to 10,000 MAU, then pay as you go. | [CF-4][BYO-2] |
| E. BYO provider: WorkOS AuthKit | AuthKit is the AS. Supports DCR and CIMD ("added to the MCP specification in November 2025"). Server verifies JWTs against the AuthKit JWKS. | Made for MCP; both registration modes; largest free tier. | Second vendor. Cloudflare Workers example not on the page I read. | "First 1M MAUs" free; "Each additional 1M MAUs $2,500/mo". | [CF-4][BYO-3] |
| F. BYO provider: Descope | Cloudflare doc: "Custom scopes for fine-grained control". Descope Inbound Apps and "MCP authentication" bill per "monthly active consent" (MAC). | Made for MCP. | Second vendor. MAC quota is small on Free. | Free 7,500 MAU and 2,000 MACs. Pro "Starts at $249/mo". | [CF-4][BYO-4] |
| G. BYO provider: Clerk | Clerk can act as the OAuth AS. Supports DCR (with a warning that it "creates a public, unauthenticated endpoint") and CIMD ("currently in beta"). | Good developer UX. | Not in Cloudflare's MCP auth doc. CIMD in beta. Second vendor. | Free 50,000 MRU. Pro "$25/mo ($20/mo billed annually)", "$0.02/mo each" over the limit. | [BYO-5][BYO-6] |
| H. Cloudflare Access (Access for SaaS, OIDC) | Access is the identity layer. "The MCP server implements the OAuth authorization code flow against Cloudflare Access". Login by one-time PIN or a linked IdP (GitHub, Google). | No code for login. Device and IP rules. | Docs describe a manual OAuth client per app; no DCR or CIMD, so Claude and ChatGPT cannot self-register against Access. Built for teams, not for paying strangers. | Free for 50 users; USD 7 per user per month above that. | [CF-5][CF-8] |

Table verdict: A plus B is the only option that stays inside one Worker, needs no new vendor, and offers CIMD, DCR, and pre-registered clients at the same time.

## 3. Tie a login to a paid plan

### Stripe pieces

| Piece | What it does | Detail | Source |
|---|---|---|---|
| Checkout Session | Hosted payment page that creates the Customer and the Subscription. | `stripe.checkout.sessions.create({ mode: 'subscription', line_items: [{ price, quantity: 1 }], success_url: '.../success?session_id={CHECKOUT_SESSION_ID}', cancel_url })`. Add `client_reference_id` or `metadata.github_user_id` so the webhook can map the payment to the login. | [ST-1] |
| Customer Portal | Hosted page for the subscriber to update the card, switch plan, or cancel. | `stripe.billingPortal.sessions.create({ customer, return_url })`, then redirect to `session.url`. Sessions expire after 5 minutes if unused. Also available as a no-code link from the Dashboard. | [ST-3] |
| Subscription status | Source of truth for access. | Give access on `trialing` and `active`. "When a subscription changes to `canceled` or `unpaid`, revoke access." `past_due`: warn the user; Stripe may retry. `incomplete` means the first payment did not finish within 23 hours. | [ST-2] |
| Webhook events | Push status changes to the Worker. | Handle `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`. "You can provision access to your product when you receive `invoice.paid` and the subscription `status` is `active`." Events are not ordered; "Track event IDs to identify duplicate deliveries". | [ST-2][ST-4] |
| Signature check on Workers | Workers have no Node `crypto`. | Use `stripe.webhooks.constructEventAsync(payload, header, secret)` with the raw body. Default tolerance is 300 s. Return 2xx fast. Stripe retries for up to 3 days in live mode. | [ST-4][ST-5] |
| Fees | Standard card fees plus Billing. | UK example: "1.5% + 20p" domestic card, "2.5% + 20p" EEA card, Billing pay as you go "0.7% of Billing volume". Custom domain for the portal: USD 10/month (optional). US and EUR numbers not read directly (see Unverified 6). | [ST-6] |

### Check at token issue time versus per request

| Check point | How | Pros | Cons |
|---|---|---|---|
| At `/authorize` (token issue) | After GitHub login, read the D1 row. If `status` not in (`active`, `trialing`), redirect to Checkout instead of calling `completeAuthorization`. | Non-payers never get a token. One page handles sign-up and renewal. | A cancel after issue still works until the access token expires. Refresh tokens do not run your code in the library, so a refresh re-issues without a check unless the TTL is short. |
| Per request (tool call) | In the tool handler, read `props.userId` from `getMcpAuthContext()`, then read the D1 row and check `status`. Reject with an MCP error text if not active. | Cancel takes effect on the next call. You need the row anyway to get `installation_id` for the repo. One D1 row read per call is inside the free 25 B rows per month. | One extra D1 read per call (sub-millisecond). |
| Both (recommended) | Do both. Keep the access token TTL short (1 hour) so refresh happens often. | Clean UX at sign-up, and fast revoke. | None that matter at this scale. |

### What to store and where

| Data | Store | Why | Source |
|---|---|---|---|
| OAuth clients, codes, access and refresh tokens, grants | KV `OAUTH_KV`, managed by `workers-oauth-provider` | Library requirement. Values are hashed; `props` encrypted. | [CF-2] |
| `subscribers` table: `github_user_id` (PK), `github_login`, `stripe_customer_id`, `stripe_subscription_id`, `status`, `current_period_end`, `installation_id`, `repo_full_name`, `updated_at` | D1 | Relational lookups by GitHub id and by Stripe customer id from the webhook. Strong consistency; KV is eventual (up to 60 s), which is wrong for "did they pay". D1 included: 25 B rows read, 50 M rows written, 5 GB. | [CF-9] |
| Processed Stripe `event.id` | D1 table `stripe_events(id PK, received_at)` | Idempotent webhook handling. | [ST-4] |
| Per-subscriber `graph-index.json` | KV key `index:<github_user_id>` | Same as the issue-14 design, one key per subscriber. 25 MiB per value. | previous research |
| GitHub App private key, GitHub App client secret, Stripe secret key, Stripe webhook secret, `COOKIE_ENCRYPTION_KEY` | Worker secrets (`wrangler secret put`) | Never in code or D1. | [CF-7] |
| GitHub repo credential per subscriber | None. Store only `installation_id`. | See next table. | [GH-1][GH-2] |

### GitHub repo access per subscriber

| Option | How | Pros | Cons | Source |
|---|---|---|---|---|
| GitHub App installation per subscriber (recommended) | Publish one public GitHub App with `Contents: Read-only`. Subscriber opens `https://github.com/apps/<APP-NAME>/installations/new?state=<nonce>` and picks "Only select repositories" for the vault repo. GitHub redirects to the app's setup URL with `installation_id`. Turn on "Request user authorization (OAuth) during installation" so GitHub also sends a `code`; exchange it for a user access token and call `GET /user/installations` to confirm the user owns that installation. Store `installation_id`. When the Worker needs the repo, sign a JWT with the app private key and `POST /app/installations/{id}/access_tokens`, optionally with `repositories` and `permissions` to narrow it. "The installation access token will expire after 1 hour." | Nothing secret stored per user. Access dies when the user uninstalls the app. Scope is one repo. Rate limit 5,000 requests per hour per installation. App webhooks deliver `push` for every installed repo, which replaces the per-repo Actions workflow from issue 14 for subscribers. | The app must be public to share the install link. "You should not rely on the validity of the `installation_id` parameter" without the user token check. | [GH-1][GH-2][GH-3][GH-4][GH-5][GH-7] |
| Fine-grained PAT pasted by the user | Subscriber creates a token limited to one repo with `Contents: Read`. The Worker stores it encrypted in D1 and uses it for API calls. | No GitHub App to register. | Default expiry 30 days; the user must rotate it. You hold a long-lived secret per user. Unauthenticated fallbacks hit 60 requests per hour. | [GH-6] |
| GitHub user access token from the GitHub App login | Store the user token from the OAuth login and read the repo as the user. | One flow. | User tokens can expire (8 hours when expiring tokens are on) and need refresh storage; they act as the user, not as the app. Broader than one repo. | [GH-3] |

Note: a GitHub App can also be the OAuth login provider for option B in section 2. GitHub Apps support "user access token" login with a callback URL. So one GitHub App covers login and repo access. [GH-3][GH-4]

## 4. Recommended path (simplest that works with all three clients)

Name: **one Worker, self-hosted OAuth with GitHub login, GitHub App for the vault, Stripe Checkout for the plan.**

Why this one:

1. All three clients support CIMD and DCR. `workers-oauth-provider` serves both from one config, plus RFC 9728 and RFC 8414 metadata. No client registration by hand. Pre-registered client IDs still work for users who want them. [AN-1][AN-2][OA-1][CF-2]
2. It stays in the one Worker from issue 14. No new vendor, no new bill. KV for tokens, D1 for subscribers, Worker secrets for keys. [CF-2][CF-9]
3. Subscribers already have GitHub. GitHub login gives a stable user id and needs no password store. The same GitHub App reads the vault with a 1-hour installation token, so the Worker never stores a user repo secret. [CF-7][GH-1][GH-2]
4. Stripe Checkout and the Customer Portal are hosted pages. The Worker needs one webhook route and one D1 table to know who paid. [ST-1][ST-2][ST-3]

Flow for a new subscriber:

1. Client sends a request to `/mcp` with no token. Worker answers 401 with `WWW-Authenticate: Bearer resource_metadata="https://<host>/.well-known/oauth-protected-resource/mcp"`. [AN-1][OA-1]
2. Client reads the metadata, then the AS metadata. It picks CIMD (Claude, ChatGPT) or DCR (fallback) or a pre-registered ID. [MCP-2]
3. Client opens `/authorize`. The Worker redirects to GitHub login (GitHub App user authorization). GitHub returns the user. [GH-3]
4. Worker reads `subscribers` by `github_user_id`.
   - No row or `status` not active: redirect to a Stripe Checkout Session with `client_reference_id = github_user_id`. On `checkout.session.completed` and `invoice.paid`, the webhook writes the row. The success page tells the user to click "Connect" again in the client.
   - Row active but no `installation_id`: redirect to `https://github.com/apps/<APP-NAME>/installations/new?state=<nonce>`. The setup URL stores `installation_id` after the user token check.
   - Row active with `installation_id`: show a one-line consent page, then `completeAuthorization({ userId: github_user_id, scope: ["context:read"], props: { userId, installationId } })`. [CF-2][ST-1][GH-4]
5. Every tool call reads `getMcpAuthContext().props.userId`, loads the D1 row, checks `status`, and loads `index:<userId>` from KV. [CF-3]
6. Stripe webhook keeps `status` current. `customer.subscription.deleted` or `unpaid` flips the row, and the next tool call is refused. [ST-2]

Worker config checklist:

- `OAuthProvider`: `apiRoute: "/mcp"`, `authorizeEndpoint: "/authorize"`, `tokenEndpoint: "/token"`, `clientRegistrationEndpoint: "/register"`, `clientIdMetadataDocumentEnabled: true`, `scopesSupported: ["context:read"]`. Keep public clients allowed (default). [CF-2]
- `wrangler.jsonc`: `compatibility_flags: ["global_fetch_strictly_public"]`, KV binding `OAUTH_KV`, KV binding `INDEX`, D1 binding `DB`. [CF-2]
- Redirect URIs: none to register by hand. CIMD and DCR carry them. The library validates them against the client document. Claude Code needs loopback with any port; check the library handles this before launch (see Unverified 3). [AN-1][MCP-2]
- GitHub App: permission `Contents: Read-only`, "Request user authorization (OAuth) during installation" on, callback `https://<host>/callback`, setup URL `https://<host>/github/setup`, webhook `https://<host>/github/webhook` for `push`. [GH-3][GH-4]
- Stripe: one Product and Price, one webhook endpoint `https://<host>/stripe/webhook` with the six events above, Customer Portal activated in the Dashboard. [ST-2][ST-3]

Cost at small scale (under 100 subscribers, under 10,000 tool calls per month): USD 0 above the existing Workers Paid plan, plus Stripe fees per payment. [CF-9][ST-6]

## Unverified

1. ChatGPT plan gating and surfaces. `help.openai.com` article 12584461 returns HTTP 403 to automated fetches. The claims "Plus, Pro, Business, Enterprise, and Education" and "web only" come from search-engine snippets. The OpenAI developer docs only say "Developer mode availability can depend on account and workspace policy." Confirm in a browser. [OA-3]
2. Whether ChatGPT shows a client ID and secret field in the developer-mode connector UI. The auth doc says organizations "can manually create OAuth clients for ChatGPT", but the connect page I read does not show the form fields. [OA-1][OA-3]
3. Whether `workers-oauth-provider` matches loopback redirect URIs with the port ignored, as Claude Code's CIMD requires (`http://localhost/callback` with any port). The README says "Exact authorization-request redirect URI validation". Test with `claude mcp add` before launch. [CF-2][AN-1]
4. Whether `workers-oauth-provider` emits the RFC 9207 `iss` parameter and sets `authorization_response_iss_parameter_supported`. Not found in the README summary. Without it, ChatGPT uses the `https://chatgpt.com/connector/oauth/{callback_id}` redirect form. [CF-2][OA-1]
5. Auth0 MCP and DCR setup pages (`/docs/get-started/apis/auth-for-mcp`, `/configure-dynamic-client-registration`) returned 404. Auth0 facts come from Cloudflare's auth doc and the Auth0 pricing page only. [CF-4][BYO-1]
6. Stripe US and EUR fees. `stripe.com/pricing` and `stripe.com/us/pricing` served a Poland page (1.5% + 1.00 zl). The UK page gave 1.5% + 20p. Check the fee for your Stripe account country. [ST-6]
7. The `setup_action` query parameter on the GitHub App setup URL redirect. The docs I read confirm `installation_id` and the `code` parameter, but I did not see `setup_action` on a primary page. [GH-4][GH-3]
8. The Cloudflare `remote-mcp-github-oauth` demo uses the `McpAgent`/Durable Object path. I did not find a `createMcpHandler` version of the GitHub login handler. Plan a small port. [CF-7]
9. Cloudflare Zero Trust free seats and price ("free up to 50 users", "$7/user/month") come from search snippets of cloudflare.com pages; the plans page did not render the numbers to the fetcher. [CF-8]

## Sources

MCP specification
- [MCP-1] Authorization (2026-07-28, current): https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization and versioning: https://modelcontextprotocol.io/specification/versioning
- [MCP-2] Client Registration (CIMD, pre-registration, DCR, priority order): https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration
- [MCP-3] Changelog 2026-07-28 (DCR deprecated, `iss`, `application_type`): https://modelcontextprotocol.io/specification/2026-07-28/changelog

Anthropic / Claude
- [AN-1] Authentication for connectors (auth types, CIMD conditions, callback URLs, token refresh, latency, egress IPs): https://claude.com/docs/connectors/building/authentication
- [AN-2] Claude Code MCP (DCR, CIMD, `--client-id`, `--callback-port`, `claude mcp login`, discovery chain): https://code.claude.com/docs/en/mcp
- [AN-3] Get started with custom connectors using remote MCP (Advanced settings client ID/secret, plans): https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp

OpenAI
- [OA-1] Authentication for plugin MCP servers (PRM, AS metadata, CIMD, DCR, pre-registered, redirect URIs, resource, token verification): https://developers.openai.com/apps-sdk/build/auth
- [OA-2] Building MCP servers for plugins and API integrations: https://developers.openai.com/api/docs/mcp
- [OA-3] Connect and test your plugin in ChatGPT (developer mode, `/mcp`): https://developers.openai.com/plugins/deploy/connect-chatgpt and help center (fetch blocked): https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt

Cloudflare
- [CF-1] MCP authorization options: https://developers.cloudflare.com/agents/model-context-protocol/authorization/
- [CF-2] `@cloudflare/workers-oauth-provider` README (endpoints, CIMD flag, `global_fetch_strictly_public`, hashed storage, `completeAuthorization`, `disallowPublicClientRegistration`): https://github.com/cloudflare/workers-oauth-provider
- [CF-3] `createMcpHandler` API (`context.http.authInfo`, `getMcpAuthContext`): https://developers.cloudflare.com/agents/model-context-protocol/apis/handler-api/
- [CF-4] Build a remote MCP server (GitHub OAuth template, BYO provider list, Access): https://developers.cloudflare.com/agents/guides/remote-mcp-server/
- [CF-5] Secure MCP servers with Access for SaaS: https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/secure-mcp-servers/
- [CF-6] McpAgent API (deprecated): https://developers.cloudflare.com/agents/model-context-protocol/mcp-agent-api/
- [CF-7] Demo `remote-mcp-github-oauth` README: https://github.com/cloudflare/ai/tree/main/demos/remote-mcp-github-oauth
- [CF-8] Zero Trust plans (numbers via search snippet): https://www.cloudflare.com/plans/zero-trust-services/
- [CF-9] D1 pricing: https://developers.cloudflare.com/d1/platform/pricing/ and KV pricing: https://developers.cloudflare.com/kv/platform/pricing/

BYO providers
- [BYO-1] Auth0 pricing: https://auth0.com/pricing
- [BYO-2] Stytch pricing: https://stytch.com/pricing and Connected Apps for MCP servers: https://stytch.com/docs/guides/connected-apps/mcp-servers
- [BYO-3] WorkOS pricing: https://workos.com/pricing and AuthKit for MCP: https://workos.com/docs/authkit/mcp
- [BYO-4] Descope pricing: https://www.descope.com/pricing
- [BYO-5] Clerk pricing: https://clerk.com/pricing
- [BYO-6] How Clerk implements OAuth (DCR, CIMD beta): https://clerk.com/docs/guides/configure/auth-strategies/oauth/how-clerk-implements-oauth

Stripe
- [ST-1] Prebuilt subscription page with Checkout (`mode: 'subscription'`, `success_url`, portal session code): https://docs.stripe.com/billing/quickstart
- [ST-2] Using webhooks with subscriptions (events, statuses, access rules): https://docs.stripe.com/billing/subscriptions/webhooks
- [ST-3] Customer portal: https://docs.stripe.com/customer-management
- [ST-4] Receive Stripe events in your webhook endpoint (signature, tolerance, retries, duplicates): https://docs.stripe.com/webhooks
- [ST-5] stripe-node `Webhooks.ts` (`constructEventAsync`, `DEFAULT_TOLERANCE = 300`): https://github.com/stripe/stripe-node/blob/master/src/Webhooks.ts
- [ST-6] Stripe pricing (UK page): https://stripe.com/en-gb/pricing

GitHub
- [GH-1] Generating an installation access token (JWT, 1 hour, `repositories`, `permissions`): https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app
- [GH-2] Authenticating as a GitHub App installation (find installation id, endpoints): https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
- [GH-3] Generating a user access token (OAuth during installation, `GET /user/installations`): https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app and about authentication: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app
- [GH-4] About the setup URL (`installation_id`, do not trust it alone): https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/about-the-setup-url and callback URL: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/about-the-user-authorization-callback-url
- [GH-5] Sharing your GitHub App (public install link, `state`): https://docs.github.com/en/apps/sharing-github-apps/sharing-your-github-app and installing your own app (repository selection): https://docs.github.com/en/apps/using-github-apps/installing-your-own-github-app
- [GH-6] Managing personal access tokens (fine-grained PAT scoping and expiry): https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
- [GH-7] REST API rate limits (installations 5,000/hour, cap 12,500): https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
