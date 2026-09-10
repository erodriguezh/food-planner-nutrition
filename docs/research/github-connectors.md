# Research: GitHub connectors in Claude Code, claude.ai and ChatGPT

Ticket: https://github.com/erodriguezh/food-planner-nutrition/issues/12
Date: 2026-09-10
Sources: primary only (Anthropic docs and help center, OpenAI help center and ChatGPT Learn docs, GitHub docs and the GitHub MCP server repository). Every claim links to the page that owns it. Items that could not be verified are listed in the "Unverified" section.

## Summary

1. **Claude Code (local clone)** does everything the vault needs: read files, edit files, commit, create branches, push, open PRs, and read a pasted or dropped image in the same session. Limits are your GitHub push limits (100 MiB per file) and your Claude plan usage. [S1][S2][S13]
2. **Claude Code on the web / mobile (cloud sessions)** also does everything: Claude clones the repo into a VM, commits on its own branch, pushes that branch, and can create a PR. You can attach a photo from the Claude iOS/Android app or claude.ai/code and Claude sees it. Push is restricted to the session's working branch. Rate limits are shared with your Claude plan. [S3][S4][S5][S6][S16]
3. **claude.ai "Add from GitHub" integration** (chat and Projects) is **read-only**: it syncs file names and contents of one branch and nothing else. No write, no commit, no branch. [S7][S8]
4. **claude.ai write path**: add GitHub's official remote MCP server (`https://api.githubcopilot.com/mcp/`) as a custom connector. It exposes `create_branch`, `create_or_update_file`, `push_files`, `get_file_contents`, and PR tools, and remote connectors work on web, desktop and mobile. Custom connectors are available on all Claude plans (Free: one connector). Anthropic also lists GitHub's MCP server in its connector directory. [S9][S10][S11][S12]
5. **ChatGPT GitHub connector** is **read-only**. OpenAI states: "The GitHub app in ChatGPT only lets you read from your repositories... To write to repositories, you need to use Codex." [S17]
6. **ChatGPT write path**: Codex cloud (in ChatGPT web, and in preview in the iOS/Android app) works on a branch, pushes, and opens PRs. Images can be attached to Codex prompts on web. Alternative: a custom MCP connector with write tools, but full MCP write actions are in beta for Business, Enterprise and Edu only, not Plus/Pro. [S18][S19][S20][S21][S22]
7. **Photo of a nutrition label -> Food node**: works end to end in Claude Code (local, web, mobile) and in Codex cloud. In plain claude.ai chat it works only if a GitHub MCP connector with write tools is added. In plain ChatGPT chat with the GitHub connector it does not work (read-only). [S4][S9][S17][S22]
8. **GitHub-side limits** apply to every MCP or API path: 5,000 REST requests/hour per user, 80 content-generating requests/minute, 500/hour; Contents API reads files up to 1 MB fully; files over 100 MiB are blocked. [S14][S15][S13]

## Capability table per runtime

Legend: Yes / No / Partial. Each cell cites its source.

### Runtime 1: Claude Code inside a local clone

| Capability | Result | Evidence |
| --- | --- | --- |
| (a) Read files | Yes | "Claude Code is an agentic coding tool that reads your codebase, edits files, runs commands". "Run it inside a notes vault, a documentation folder, or any collection of markdown files to search, edit, and reorganize content the same way you would code." [S1][S2] |
| (b) Write and commit | Yes | "Claude Code works directly with git. It stages changes, writes commit messages, creates branches, and opens pull requests." [S1] |
| (c) Create branches | Yes | Same sentence as above. [S1] |
| (d) Image in conversation, then write a file | Yes | "Drag and drop an image into the Claude Code window", "Copy an image and paste it into the CLI with Ctrl+V", "Provide an image path to Claude." Claude then edits files normally. [S2] |
| (e) Limits | Plan usage limits; git push limits: warning at 50 MiB, block at 100 MiB per file; recommended repo size under 1 GB. | [S13] Plan limits are not enumerated in the Claude Code docs (see Unverified U1). |

### Runtime 2: Claude Code on the web and Claude mobile app (cloud sessions)

| Capability | Result | Evidence |
| --- | --- | --- |
| (a) Read files | Yes | "Claude clones it into an isolated virtual machine, makes changes, and pushes a branch for you to review." [S3] |
| (b) Write and commit | Yes | "Push the branch: when Claude reaches a stopping point, it pushes its branch to GitHub. You review the diff, leave inline comments, create a PR, or send another message to keep going." Commits carry a `Claude-Session: <url>` trailer. [S3][S5] |
| (c) Create branches | Yes, one branch per session | "Each task gets its own session and its own branch". Push protection: "`git push` works only against the session's current working branch". [S3][S5] |
| (d) Image in conversation, then write a file | Yes | "Send images and files from your phone or browser: attach a photo or file in the Claude app or at claude.ai/code, with or without a caption. Claude sees attached photos directly as part of your message." (stated on the Remote Control page; see U2 for the cloud-session nuance) Mobile: "Photos: Claude sees attached photos directly as part of your message. Claude Code also saves each photo under `~/.claude/uploads/`". [S16][S4] |
| (e) Limits | Shares your Claude plan rate limits; no separate VM charge. Any repo the connected GitHub account can see. Network: GitHub goes through a proxy; GraphQL is limited to a pinned set of PR operations. Bundled non-GitHub repos: under 100 MB. Plans: Pro, Max, Team, Enterprise (premium seat). | "Claude Code on the web shares rate limits with all other Claude and Claude Code usage within your account." "a cloud session can access any repository the connecting GitHub account can see". [S3][S5][S6] |

### Runtime 3: claude.ai (web, desktop, mobile)

Two distinct mechanisms exist. They must not be confused.

**3a. Built-in "Add from GitHub" integration (chat "+" menu and Project knowledge)**

| Capability | Result | Evidence |
| --- | --- | --- |
| (a) Read files | Yes | Retrieved: "File names, File contents, Branch content". Not retrieved: "Commit history, Pull requests, Issues, Repository metadata". [S7] |
| (b) Write and commit | No | "Only files (names and contents) in a repo on a specific branch are synced." No write operation is documented. [S8] |
| (c) Create branches | No | Not documented; the integration only reads a selected branch. [S7][S8] |
| (d) Image then write | No (write is impossible) | Image upload itself works: JPEG, PNG, GIF, WebP, up to 20 files per chat; iOS/Android widget has a camera button. [S23][S24][S25] |
| (e) Limits | Content must fit the context window; manual "Sync now"; all plans including Free. | "add multiple repositories ... provided they fit within Claude's context window." "Available on all plans including Free." [S7] |

**3b. GitHub MCP server added as a connector (remote MCP)**

| Capability | Result | Evidence |
| --- | --- | --- |
| (a) Read files | Yes | GitHub MCP server repos toolset: `get_file_contents` "Get file or directory contents", `list_branches`. [S9] |
| (b) Write and commit | Yes | Tools `create_or_update_file` "Create or update file", `push_files` "Push files to repository", `delete_file`. Each write is a commit on the target branch (GitHub Contents API semantics: "Creates a new file or replaces an existing file in a repository", direct commit to `branch`). [S9][S15] |
| (c) Create branches | Yes | Tool `create_branch` "Create branch". [S9] |
| (d) Image then write | Yes, in principle | Image goes into the chat as in 3a; Claude then calls the write tool. Anthropic: MCP servers can enable "Creating, modifying, or deleting data in connected applications" and Claude shows tool approval requests. Not tested end to end here (see U3). [S10][S23] |
| (e) Limits | Custom connectors on Free, Pro, Max, Team, Enterprise; Free: one custom connector. Remote connectors work on "web, mobile, Claude Cowork, Claude Desktop, and Claude Code". GitHub API: 5,000 req/h per user; 80 content-generating req/min, 500/h. Contents API: full features up to 1 MB per file. | [S10][S11][S14][S15] |

Auth note: the GitHub MCP remote server states "Each MCP host application needs to configure a GitHub App or OAuth App to support remote access via OAuth. Any host application that supports remote MCP servers should support the remote GitHub server with PAT authentication." Claude Code documents the PAT header path (`claude mcp add --transport http github https://api.githubcopilot.com/mcp/ --header "Authorization: Bearer YOUR_GITHUB_PAT"`). Whether claude.ai's custom connector UI completes GitHub's OAuth flow was not verified (U4). A read-only variant exists at `https://api.githubcopilot.com/mcp/readonly`. [S9][S12][S26]

Connector sharing: connectors added at claude.ai/customize/connectors "are automatically available in Claude Code" when signed in with the claude.ai account. [S26]

### Runtime 4: ChatGPT (web, desktop, mobile)

**4a. Built-in GitHub connector (chat, deep research)**

| Capability | Result | Evidence |
| --- | --- | --- |
| (a) Read files | Yes | "ChatGPT can pull live data from your repositories—code, README files, and other docs—and reason over it in real time." [S17] |
| (b) Write and commit | No | "The GitHub app in ChatGPT only lets you read from your repositories to analyze and search your code. To write to repositories, you need to use Codex to generate, edit, and push code directly to GitHub." [S17] |
| (c) Create branches | No | Read-only per above. [S17] |
| (d) Image then write | No (write is impossible) | Image upload works: PNG, JPEG, non-animated GIF, 20 MB per image; on mobile "tap the + icon ... Add photos & files". [S27][S28] |
| (e) Limits | Available to Plus/Pro/Team globally; Enterprise/Edu connectors default off until admin enables. ~5 minute delay before repos appear. No repo-count limit documented. | [S17][S29] |

**4b. Codex cloud (write path)**

| Capability | Result | Evidence |
| --- | --- | --- |
| (a) Read files | Yes | "Connect GitHub or GitLab (Beta) when prompted. For GitHub, choose the repositories Codex can access". [S18] |
| (b) Write and commit | Yes | "Ask Codex to make follow-up changes, or open a pull request when the work is ready". On PRs: Codex "can push a fix back to the branch when it has permission to do so." [S18][S19] |
| (c) Create branches | Yes | Task list shows Codex branches such as `codex/csv-export`; each task works on its own branch. [S18] |
| (d) Image then write | Yes on web | "Attach, paste, or drag an image into the interactive composer" (Codex accepts PNG and JPEG). Codex web supports image attachments in prompts. Mobile: see U5. [S20][S21] |
| (e) Limits | Included across ChatGPT plans including Free and Go. "Local messages and cloud chats share your plan's usage allowance." Cloud chats "may use more of your allowance than local messages." Internet: "By default, Codex blocks internet access during the agent phase" (GitHub itself is reachable). | [S22][S30][S31] |

**4c. Custom MCP connector with write tools (Developer mode)**

| Capability | Result | Evidence |
| --- | --- | --- |
| Write via MCP | Partial (plan-gated) | "Full MCP (Model Context Protocol) support, including modify/write actions, is rolling out in beta to ChatGPT Business, Enterprise, and Edu plans." "OpenAI-built apps are search-only today and do not support write actions." Confirmation modal is shown before write actions. Plus/Pro: read/search custom connectors only. [S32] |

## Recommended write path per runtime

| Runtime | Recommended path | Why |
| --- | --- | --- |
| Claude Code, local clone | Native git in the clone: edit, `git commit`, `git push`, `gh pr create`. | Full capability, no extra setup. [S1] |
| Claude Code web / Claude mobile app | Start a cloud session on the vault repo. Attach the label photo. Claude writes the Food node, commits on the session branch, pushes; create a PR from the diff view or let Claude merge via `gh`. | Full capability including photos; branch-per-session is safe for a vault. Push is limited to the session branch, so plan a merge step (PR or `gh pr merge`). [S3][S5][S16] |
| claude.ai chat (web/desktop/mobile) | Add GitHub's remote MCP server `https://api.githubcopilot.com/mcp/` as a custom connector (fine-grained PAT scoped to the vault repo, or OAuth if the UI supports it). Use `get_file_contents` to read `index.md`/`state.md`, and `push_files` to commit several files in one commit. Keep the built-in "Add from GitHub" only for read-only context. | Built-in integration cannot write. MCP tools write directly to a branch. [S7][S9][S10] |
| ChatGPT chat (web/desktop/mobile) | Do not use the GitHub connector for writes. Route writes through Codex cloud: connect the vault repo to Codex, attach the photo, ask Codex to create the Food node and open a PR. | GitHub connector is read-only; Codex is OpenAI's stated write path. [S17][S18] |
| ChatGPT Business/Enterprise only | Optional: add the GitHub MCP server as a custom MCP connector in Developer mode for direct writes from chat. | Full MCP write actions are beta on Business/Enterprise/Edu only. [S32] |
| Any runtime, fallback | Claude Code GitHub Actions: `@claude` in an issue or comment; the Action can "analyze code, implement changes, and push commits" and create PRs with the Claude GitHub App (Contents, Issues, Pull requests read/write). | Works from any client that can open a GitHub issue. Image-in-issue handling not verified (U6). [S33] |

Design consequence for the vault: every automated write should target a branch, not `main`, because the cloud paths (Claude Code web, Codex) already produce branches, and `push_files`/`create_or_update_file` accept a `branch` parameter. A small merge step (PR auto-merge or a scheduled routine) keeps `index.md` and `state.md` consistent.

## Unverified

- U1. Exact Claude plan rate limits (messages or tokens per period) for Claude Code and claude.ai. The Claude Code docs only state that cloud sessions share account rate limits. Not enumerated in any fetched primary page.
- U2. Whether photo attachments are accepted in **Anthropic-hosted cloud sessions** specifically. The sentence "attach a photo or file in the Claude app or at claude.ai/code" appears on the Remote Control page, and the mobile page states photo handling under the Remote Control section. The cloud-session pages (web quickstart, Claude Code on the web) do not mention image attachments explicitly. Needs a hands-on test.
- U3. End-to-end test of claude.ai chat + GitHub MCP connector: image in, `push_files` out. Documented tool capabilities support it; not executed here.
- U4. Whether the claude.ai custom connector dialog completes GitHub's OAuth flow for `https://api.githubcopilot.com/mcp/`, or whether a PAT header is required (claude.ai custom connector UI documents OAuth Client ID/Secret fields, not arbitrary headers). GitHub's statement: OAuth needs a host-side GitHub/OAuth App; PAT works on any host.
- U5. Codex in the ChatGPT **mobile** app: the OpenAI help article states a preview on iOS and Android, but help.openai.com returned HTTP 403 to direct fetches, so the wording is known only from search excerpts. Whether you can start a **cloud** task with a photo from mobile (rather than drive a desktop host through Remote) was not confirmed on a fetchable page.
- U6. Whether Claude Code GitHub Actions passes images embedded in an issue or comment to Claude. Not documented on the fetched page.
- U7. Anthropic's connector directory entry "GitHub MCP Connector" (https://claude.com/connectors/github): the page renders client-side; only the search index description ("read repositories and code files, manage issues and PRs, analyze code, and automate workflows", "Official GitHub MCP Server") was readable. Plan gating for that directory entry was not visible.
- U8. All help.openai.com pages ([S17][S27][S29][S32]) returned HTTP 403 to direct fetch (bot protection). Facts from those pages come from search-engine excerpts of the official pages. Re-verify in a browser before relying on exact wording.
- U9. GitHub MCP server rate limits: the server documents none of its own; the assumption is that GitHub REST limits [S14] apply to the underlying calls.

## Sources

- [S1] Claude Code overview: https://code.claude.com/docs/en/overview
- [S2] Claude Code common workflows (images, notes vaults, PRs): https://code.claude.com/docs/en/common-workflows
- [S3] Get started with Claude Code on the web: https://code.claude.com/docs/en/web-quickstart
- [S4] Claude Code on mobile: https://code.claude.com/docs/en/mobile
- [S5] Configure cloud environments (GitHub proxy, push protection, gh, network): https://code.claude.com/docs/en/cloud-environments
- [S6] Use Claude Code on the web (limitations, rate limits, auth): https://code.claude.com/docs/en/claude-code-on-the-web
- [S7] GitHub integration (claude.com docs): https://claude.com/docs/connectors/github
- [S8] Use the GitHub integration (help center): https://support.claude.com/en/articles/10167454-use-the-github-integration
- [S9] GitHub MCP server README (tools, remote URL, OAuth/PAT, read-only): https://github.com/github/github-mcp-server and https://raw.githubusercontent.com/github/github-mcp-server/main/README.md
- [S10] Get started with custom connectors using remote MCP: https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- [S11] When to use desktop and web connectors: https://support.claude.com/en/articles/11725091-when-to-use-desktop-and-web-connectors
- [S12] GitHub MCP remote server doc (readonly and toolset URLs): https://raw.githubusercontent.com/github/github-mcp-server/main/docs/remote-server.md
- [S13] About large files on GitHub: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- [S14] Rate limits for the REST API: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- [S15] REST API: repository contents: https://docs.github.com/en/rest/repos/contents
- [S16] Remote Control (attach photo or file from Claude app or claude.ai/code): https://code.claude.com/docs/en/remote-control
- [S17] Connecting GitHub to ChatGPT (read-only statement): https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt
- [S18] Codex cloud: https://learn.chatgpt.com/docs/cloud
- [S19] Use Codex with GitHub (reviews, push fixes to branch): https://learn.chatgpt.com/docs/third-party/github
- [S20] Image inputs (ChatGPT Learn): https://learn.chatgpt.com/docs/image-inputs
- [S21] Prompting (Codex, images): https://developers.openai.com/codex/workflows
- [S22] Using Codex with your ChatGPT plan: https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- [S23] Upload files to Claude (image formats and limits): https://support.claude.com/en/articles/8241126-upload-files-to-claude
- [S24] Use Claude app intents, shortcuts, and widgets on iOS (camera button): https://support.claude.com/en/articles/10263469-use-claude-app-intents-shortcuts-and-widgets-on-ios
- [S25] Use the Claude widget on Android (camera button): https://support.claude.com/en/articles/10534883-use-the-claude-widget-on-android
- [S26] Claude Code MCP (connectors from claude.ai; GitHub remote server with PAT): https://code.claude.com/docs/en/mcp
- [S27] ChatGPT Image Inputs FAQ: https://help.openai.com/en/articles/8400551-image-inputs-for-chatgpt-faq
- [S28] File Uploads FAQ: https://help.openai.com/en/articles/8555545-file-uploads-faq
- [S29] Apps in ChatGPT (connectors, plan availability): https://help.openai.com/en/articles/11487775-connectors-in-chatgpt
- [S30] Codex pricing and usage limits: https://learn.chatgpt.com/docs/pricing
- [S31] Codex agent internet access: https://learn.chatgpt.com/docs/cloud/internet-access
- [S32] Developer mode and MCP apps in ChatGPT: https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- [S33] Claude Code GitHub Actions: https://code.claude.com/docs/en/github-actions
- [S34] Using the GitHub MCP Server (GitHub Docs): https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/use-the-github-mcp-server
- [S35] Set up the GitHub MCP Server (remote URL, OAuth/PAT): https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp-in-your-ide/set-up-the-github-mcp-server
- [S36] Claude Code feature availability by plan: https://code.claude.com/docs/en/feature-availability
