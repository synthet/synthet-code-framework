# Fleet Agent Compendium: Complete Inventory & Architecture

> **Fleet Scope**: 63 Projects across `D:\Projects` + User/Global configuration across 5 harnesses: Claude Code, Cursor, Codex, Grok, and Antigravity (Agy).
> **Report Type**: Public / Open-Source (synthet-code-framework)
> **Timestamp**: 2026-10-19

## 1. Executive Summary & Fleet Metrics

| Metric | Count | Details |
|---|---|---|
| **Projects Analyzed** | 63 | Eligible maintained: 42, upstream/archives: 21 |
| **Total Asset Files** | 36,493 | Registered agent configurations and code artifacts |
| **Unique Content Hashes** | 6,365 | Deduplicated distinct content versions |
| **Unique Skills** | 440 | 10,695 total deployed copies |
| **Unique Slash Commands** | 129 | 2,993 total deployed copies |
| **Unique Subagents** | 58 | 1,092 total deployed copies |
| **Unique Hooks** | 72 | 8 native agent hook groups (64 frontend UI hooks excluded) |
| **Distinct MCP Server Configs** | 63 | Spanning 273 configuration files |

---

## 2. Multi-Harness Architecture & Discovery

| Harness | Global Skills Path | Global Rules Path | Global Commands Path | Global MCP Config |
|---|---|---|---|---|
| **Claude Code** | `~/.claude/skills/` | `~/.claude/rules/`, `CLAUDE.md` | `~/.claude/commands/` | `~/.claude.json` |
| **Cursor** | `~/.cursor/skills/` | `~/.cursor/rules/*.mdc` | `~/.cursor/commands/` | `~/.cursor/mcp.json` |
| **Codex** | `~/.agents/skills/` | `AGENTS.md` | Via agent definitions | `~/.codex/config.toml` |
| **Antigravity (Agy)** | `~/.gemini/config/skills/` | `~/.gemini/config/rules/`, `GEMINI.md` | Native slash commands | `~/.gemini/config/mcp_config.json` |
| **Grok** | `~/.grok/bundled/skills/` | `~/.grok/rules/` | Native CLI commands | `~/.grok/config.toml` |

---

## 3. Skills Compendium

### 3.1. Framework Core & Specialist Shareable Skills (Public / Open-Source)
These skills form the reusable foundation in `synthet-code-framework` and are deployed to all harnesses globally.

| Skill Name | Scope | Unique Versions | Projects Deployed | Description |
|---|---|---|---|---|
| `agent-memory` | Core/Shareable | 20 | 45 | Log agent sessions, consolidate project memory (dream), promote reviewed memory, and load  |
| `agent-runtime-handoff` | Core/Shareable | 4 | 8 | Clarify what lives in the agent-sdlc editor kit vs what belongs in the application runtime |
| `agent-setup` | Core/Shareable | 3 | 42 | Use when inventorying, unifying, installing or synchronizing local Claude Code, Codex, Cur |
| `architecture-decisions` | Core/Shareable | 3 | 42 | Use when documenting an architecture decision, comparing consequential alternatives, or cr |
| `archive-session-transcripts` | Core/Shareable | 6 | 6 | Scan one or several projects for exported agent session transcripts, convert them into int |
| `autonomous-run-contract` | Core/Shareable | 11 | 45 | Use before letting an agent run without step-by-step supervision — unattended or overnight |
| `backlog-queue` | Core/Shareable | 12 | 45 | Cross-repo GitHub Project board is the canonical task queue. Use whenever picking work, cl |
| `cli-tools-overview` | Core/Shareable | 4 | 44 | Use as the router for agent CLI workflows: installing tools, choosing safe shell patterns, |
| `codebase-size-audit` | Core/Shareable | 6 | 10 | Read-only scan for files ≥1000 LoC and functions/methods ≥150 LoC across image-scoring-pip |
| `commit-and-push` | Core/Shareable | 7 | 45 | Use when the user asks to commit and push, publish, ship, or prepare a release commit. Gui |
| `commit-conventions` | Core/Shareable | 7 | 45 | Apply Conventional Commits and consistent PR titles when the user asks for commit messages |
| `consume` | Core/Shareable | 3 | 4 | Use when ingesting, compiling, rendering, or cleaning up documents from Downloads folders  |
| `container-operations` | Core/Shareable | 3 | 10 | Use for Docker or Compose service diagnostics, local rebuilds, container health checks, an |
| `critical-commit-audit` | Core/Shareable | 8 | 45 | Deep bug-finding on recent commits: high-severity correctness only (data loss, crashes, se |
| `data-config-tools` | Core/Shareable | 4 | 44 | Use when inspecting, querying, validating, or editing JSON, YAML, TOML, CSV, HTTP response |
| `database-backups` | Core/Shareable | 3 | 10 | Use when taking a database backup, validating a dump, or planning recovery before a migrat |
| `database-migrations` | Core/Shareable | 5 | 11 | Use when creating or reviewing schema migrations, changing deployed tables, or planning a  |
| `electron-development` | Core/Shareable | 3 | 7 | Use when changing an Electron main/preload/renderer contract, IPC handler, desktop databas |
| `eval` | Core/Shareable | 8 | 45 | Capture task quality signals and log them to agent memory to build a feedback loop. Use at |
| `export-chat` | Core/Shareable | 5 | 42 | Use when the user types /export or /export-chat, or asks to export, save, dump, copy, or s |
| `feature-flag-lifecycle` | Core/Shareable | 3 | 6 | Use when adding, promoting, testing, or removing a feature flag or staged rollout. |
| `framework-analyze` | Core/Shareable | 6 | 41 | Explicit framework workflow: analyze |
| `framework-audit-instructions` | Core/Shareable | 4 | 41 | Explicit framework workflow: audit-instructions |
| `framework-check-subagents` | Core/Shareable | 12 | 41 | Explicit framework workflow: check-subagents |
| `framework-clarify` | Core/Shareable | 8 | 41 | Explicit framework workflow: clarify |
| `framework-compile-skill` | Core/Shareable | 8 | 41 | Explicit framework workflow: compile-skill |
| `framework-decompose` | Core/Shareable | 8 | 41 | Explicit framework workflow: decompose |
| `framework-dream-memory` | Core/Shareable | 7 | 41 | Explicit framework workflow: dream-memory |
| `framework-implement` | Core/Shareable | 12 | 41 | Explicit framework workflow: implement |
| `framework-log-session` | Core/Shareable | 7 | 41 | Explicit framework workflow: log-session |
| `framework-memory-context` | Core/Shareable | 7 | 41 | Explicit framework workflow: memory-context |
| `framework-mine` | Core/Shareable | 8 | 41 | Explicit framework workflow: mine |
| `framework-plan` | Core/Shareable | 13 | 41 | Explicit framework workflow: plan |
| `framework-pr-ready` | Core/Shareable | 13 | 41 | Explicit framework workflow: pr-ready |
| `framework-promote-memory` | Core/Shareable | 7 | 41 | Explicit framework workflow: promote-memory |
| `framework-release-notes` | Core/Shareable | 6 | 41 | Explicit framework workflow: release-notes |
| `framework-run-codex-review` | Core/Shareable | 8 | 41 | Explicit framework workflow: run-codex-review |
| `framework-run-gemini-review` | Core/Shareable | 9 | 41 | Explicit framework workflow: run-gemini-review |
| `framework-run-subagent-review` | Core/Shareable | 9 | 41 | Explicit framework workflow: run-subagent-review |
| `framework-spec` | Core/Shareable | 9 | 41 | Explicit framework workflow: spec |
| `framework-task-claim` | Core/Shareable | 9 | 41 | Explicit framework workflow: task-claim |
| `framework-tasks` | Core/Shareable | 7 | 41 | Explicit framework workflow: tasks |
| `framework-test-and-fix` | Core/Shareable | 10 | 41 | Explicit framework workflow: test-and-fix |
| `framework-wiki-ingest` | Core/Shareable | 10 | 41 | Explicit framework workflow: wiki-ingest |
| `framework-wiki-lint` | Core/Shareable | 11 | 41 | Explicit framework workflow: wiki-lint |
| `framework-wiki-query` | Core/Shareable | 10 | 41 | Explicit framework workflow: wiki-query |
| `git-and-diff-workflows` | Core/Shareable | 5 | 44 | Use for safe Git and GitHub workflows: status, diffs, logs, branches, staging, commits, PR |
| `gradio-development` | Core/Shareable | 3 | 6 | Use when extending a Gradio Blocks app, event graph, session state, background job UI, or  |
| `graphify-knowledge-graph` | Core/Shareable | 3 | 44 | Use when querying architecture, concept paths, god nodes, or communities via Graphify MCP  |
| `hook-loopback-safety` | Core/Shareable | 4 | 9 | Implement hook event ingestion, normalization, blocking approvals, and loopback queue safe |
| `install-checklist` | Core/Shareable | 5 | 44 | Use when provisioning a human workstation with agent CLI tools via winget, apt, or Homebre |
| `jev-mcp` | Core/Shareable | 12 | 45 | Use Jev MCP (jev-rw-systemone) for semantic decisions a coding agent should not guess — co |
| `judge-panel` | Core/Shareable | 3 | 9 | Run a blind panel of agentic CLI vision judges (Claude, Codex, Antigravity, Cursor) over r |
| `karpathy-guidelines` | Core/Shareable | 7 | 45 | Apply Karpathy's anti-pattern checklist before/during non-trivial coding — surface assumpt |
| `lesson-to-skill` | Core/Shareable | 12 | 45 | Use at the end of a session, after a correction, or when the user says bake this in, turn  |
| `lint-format-security` | Core/Shareable | 5 | 44 | Use when running or choosing bounded linters, formatters, type checks, or security scanner |
| `llm-wiki` | Core/Shareable | 8 | 45 | Use when searching, asking, ingesting, compiling, reviewing, refreshing, validating, or an |
| `logging-and-error-reporting` | Core/Shareable | 4 | 10 | Use when adding or reviewing logging, telemetry, tracing, or error reporting. |
| `mcp-code-intelligence` | Core/Shareable | 7 | 45 | Compare MCP code-intelligence layers — CLI wrappers, ast-grep, symbol/graph tools, Zoekt,  |
| `mcp-server-design` | Core/Shareable | 9 | 45 | Design and implement an MCP server's tools, resources, and prompts with safe transport and |
| `release-bump` | Core/Shareable | 5 | 45 | Bump semver + promote CHANGELOG Unreleased via compiled harness. Use for /release, version |
| `resume-task` | Core/Shareable | 5 | 42 | Resume a previous or ongoing piece of work from wherever it was left — in Claude Code, Ope |
| `rust-testing` | Core/Shareable | 3 | 44 | Use when writing or running Rust unit tests with cargo or nextest. Apply for crate-level t |
| `safe-command-patterns` | Core/Shareable | 5 | 44 | Use before running shell commands that explore, edit, delete, move, generate, or inspect m |
| `search-and-navigation` | Core/Shareable | 5 | 44 | Use for fast repo navigation and discovery with rg, fd/find, bat/sed, tree, eza, zoxide, o |
| `search-tool-selection` | Core/Shareable | 6 | 44 | Use before any code-finding task to choose fd/find vs rg vs ast-grep vs semgrep vs fff MCP |
| `security-review` | Core/Shareable | 7 | 45 | Lightweight security sanity check before merge or when the user asks for a security pass — |
| `skill-authoring` | Core/Shareable | 9 | 45 | Use when creating, reviewing, or improving first-party agent skills in this repo. Apply wh |
| `structural-code-search` | Core/Shareable | 4 | 44 | Use when syntax-aware search is needed with ast-grep, semgrep, or ctags, especially after  |
| `subagent-review` | Core/Shareable | 12 | 45 | Runs detect_subagents then run_subagent (codex/gemini) in review mode via subagent-orchest |
| `systematic-debugging` | Core/Shareable | 6 | 45 | Use when encountering a bug, failing test, build failure, unexpected behavior, flaky behav |
| `task-env-package-tools` | Core/Shareable | 11 | 44 | Use for synthet-code-framework task runners, uv, Docker, sync checks, frontmatter validati |
| `test-driven-development` | Core/Shareable | 6 | 45 | Use when implementing a feature, bug fix, refactor, or behavior change that can be tested. |
| `threat-modeling-agentic-tools` | Core/Shareable | 8 | 45 | Threat-model agentic tooling — MCP/tool abuse, hook/prompt injection, remote control surfa |
| `typescript-monorepo-quality` | Core/Shareable | 4 | 11 | Use when changing TypeScript workspace packages, shared schemas, dependency direction, or  |
| `unity-testing` | Core/Shareable | 3 | 5 | Use when running or diagnosing Unity EditMode/PlayMode tests, batch validation, compile fa |
| `validate-implementation` | Core/Shareable | 8 | 45 | Verify implementation against spec AC-n criteria via compiled harness. Use after /implemen |
| `verification-before-completion` | Core/Shareable | 10 | 45 | Use before claiming work is complete, fixed, passing, ready to commit, or ready for PR. Ap |
| `windows-agent-tooling` | Core/Shareable | 7 | 44 | Use for native Windows agent workflows involving PowerShell, winget, Cursor IDE, Docker De |
| `windows-keep-awake` | Core/Shareable | 4 | 10 | Prevent Windows sleep and display timeout via SetThreadExecutionState. Use when the user a |
| `wsl2-agent-tooling` | Core/Shareable | 4 | 44 | Use for WSL2 Ubuntu agent workflows: repos under Linux filesystem, apt tooling, builds/tes |

### 3.2. Private & Machine-Specific Skills (`vault`)
These skills contain machine paths, disk cleaning rules, or private workflows and belong in `vault`.

| Skill Name | Target | Description |
|---|---|---|
| `windows-disk-cleanup` | `vault` | Windows C: free-space pressure, cache bloat, c-cleanup scan/analyze/report/quarantine, WinSxS cleanup. |
| `wiki-db-backup` | `vault` | Back up and restore LLM Wiki local SQLite database, WAL archiving, integrity checks. |
| `backup-repo` | `vault` | Local repository backup to personal cloud storage. |

### 3.3. Project-Specific Skills (Strictly Local)
These skills are tightly coupled to domain models, custom engines, or specialized game toolsets and must NOT be installed globally.

| Project | Skills Count | Representative Skills |
|---|---|---|
| **warp** | 47 | `add-feature-flag`, `add-telemetry`, `agent-add-mcp`, `change-keybinding`, `changelog-draft` (+42 more) |
| **image-scoring-skills** | 36 | `antigravity-cli`, `bird-crop-label`, `codex-cli`, `commit-push`, `dxo-pureraw` (+31 more) |
| **nwn-modules** | 23 | `adr`, `compile`, `diff-summary`, `docker-ops`, `find-symbol` (+18 more) |
| **image-scoring** | 20 | `antigravity-cli`, `bird-crop-label`, `codex-cli`, `commit-push`, `design-tokens` (+15 more) |
| **cursor-telegram-bot** | 14 | `framework-bootstrap-project`, `framework-hook-policy-review`, `framework-implement-feature`, `framework-mcp-tool-review`, `framework-release-check` (+9 more) |
| **heroes-templates** | 12 | `dual-repo-git`, `framework-deploy-max8`, `framework-git-commit`, `framework-git-publish`, `framework-git-push-private` (+7 more) |
| **project-twelve** | 9 | `assets-submodule-publish`, `changelog`, `framework-fetch-remotes`, `framework-pick-next-task`, `framework-publish-assets-submodule` (+4 more) |
| **image-scoring-backend** | 9 | `framework-backlog-housekeeping`, `framework-backup-db`, `framework-import-transcripts`, `framework-restore-db`, `project-rule-external-cli-subagents` (+4 more) |
| **zed** | 7 | `brand-writer`, `create-skill`, `framework-draft`, `gpui-test`, `humanizer` (+2 more) |
| **enshrouded-tools** | 6 | `enshrouded-eml`, `enshrouded-kfc`, `enshrouded-native`, `enshrouded-reflection`, `enshrouded-server-query` (+1 more) |
| **win-gui-mcp** | 6 | `framework-bootstrap-phase1`, `framework-implement-tool`, `framework-mcp-tool-review`, `framework-phase-gate`, `win-gui-mcp-implementation` (+1 more) |
| **birdweather-telegram-bot** | 6 | `framework-deploy-hetzner`, `framework-merge-open-prs`, `framework-release-and-push`, `hetzner-hcloud-deploy`, `merge-open-prs` (+1 more) |
| **synthet-llm-wiki** | 4 | `framework-consume`, `framework-wiki-maintain`, `framework-wiki-review`, `wiki-db-backup` |
| **image-scoring-gallery** | 3 | `gallery-electron-ts`, `project-rule-external-cli-subagents`, `project-rule-graphify` |
| **video-gallery** | 2 | `driftara-video-mcp`, `video-electron-ts` |
| **agent-sdlc** | 2 | `framework-constitution`, `framework-eval` |
| **rea** | 2 | `rea-tool-design`, `reverse-engineer-anything` |
| **lightroom-mcp** | 1 | `Memory MCP` |
| **mcp-agent-mailbox** | 1 | `agent-mailbox` |
| **burstpick-re** | 1 | `backup-repo` |
| **image-scoring-ui** | 1 | `design-tokens` |
| **everypixel-mcp** | 1 | `everypixel-mcp` |
| **_backup** | 1 | `firebird-db` |
| **synthet-agent-swarm** | 1 | `framework-run-antigravity-review` |

---

## 4. Slash Commands Compendium

| Command | Copies Across Fleet | Projects | Purpose / Summary |
|---|---|---|---|
| `/compile-skill` | 236 | 45 | Core workflow lifecycle command (`compile-skill`) |
| `/mine` | 169 | 45 | Core workflow lifecycle command (`mine`) |
| `/decompose` | 167 | 45 | Core workflow lifecycle command (`decompose`) |
| `/implement` | 100 | 45 | Core workflow lifecycle command (`implement`) |
| `/pr-ready` | 100 | 45 | Core workflow lifecycle command (`pr-ready`) |
| `/spec` | 100 | 45 | Core workflow lifecycle command (`spec`) |
| `/test-and-fix` | 100 | 45 | Core workflow lifecycle command (`test-and-fix`) |
| `/wiki-ingest` | 100 | 45 | Core workflow lifecycle command (`wiki-ingest`) |
| `/wiki-lint` | 100 | 45 | Core workflow lifecycle command (`wiki-lint`) |
| `/wiki-query` | 100 | 45 | Core workflow lifecycle command (`wiki-query`) |
| `/analyze` | 98 | 45 | Core workflow lifecycle command (`analyze`) |
| `/check-subagents` | 98 | 45 | Core workflow lifecycle command (`check-subagents`) |
| `/clarify` | 98 | 45 | Core workflow lifecycle command (`clarify`) |
| `/dream-memory` | 98 | 45 | Core workflow lifecycle command (`dream-memory`) |
| `/log-session` | 98 | 45 | Core workflow lifecycle command (`log-session`) |
| `/memory-context` | 98 | 45 | Core workflow lifecycle command (`memory-context`) |
| `/promote-memory` | 98 | 45 | Core workflow lifecycle command (`promote-memory`) |
| `/release-notes` | 98 | 45 | Core workflow lifecycle command (`release-notes`) |
| `/run-codex-review` | 98 | 45 | Core workflow lifecycle command (`run-codex-review`) |
| `/run-gemini-review` | 98 | 45 | Core workflow lifecycle command (`run-gemini-review`) |
| `/run-subagent-review` | 98 | 45 | Core workflow lifecycle command (`run-subagent-review`) |
| `/task-claim` | 98 | 45 | Core workflow lifecycle command (`task-claim`) |
| `/tasks` | 98 | 45 | Core workflow lifecycle command (`tasks`) |
| `/plan` | 97 | 45 | Core workflow lifecycle command (`plan`) |
| `/audit-instructions` | 88 | 43 | Core workflow lifecycle command (`audit-instructions`) |
| `/critical-commit-audit` | 14 | 5 | Core workflow lifecycle command (`critical-commit-audit`) |
| `/release` | 14 | 5 | Core workflow lifecycle command (`release`) |
| `/backlog-housekeeping` | 8 | 3 | Core workflow lifecycle command (`backlog-housekeeping`) |
| `/backup-db` | 8 | 3 | Core workflow lifecycle command (`backup-db`) |
| `/import-transcripts` | 8 | 3 | Core workflow lifecycle command (`import-transcripts`) |
| `/restore-db` | 8 | 3 | Core workflow lifecycle command (`restore-db`) |
| `/review` | 5 | 3 | Core workflow lifecycle command (`review`) |
| `/off` | 4 | 3 | Core workflow lifecycle command (`off`) |
| `/on` | 4 | 3 | Core workflow lifecycle command (`on`) |
| `/next-steps` | 4 | 2 | Core workflow lifecycle command (`next-steps`) |

---

## 5. Subagents Compendium & Version Drift

| Subagent Name | Copies Across Fleet | Unique Versions (Drift) | Status / Action |
|---|---|---|---|
| `critical-commit-audit` | 184 | 14 versions | Standardized to canonical definition |
| `external-cli-reviewer` | 184 | 48 versions | Standardized to canonical definition |
| `external-codex-review` | 184 | 48 versions | Standardized to canonical definition |
| `external-gemini-review` | 184 | 48 versions | Standardized to canonical definition |
| `pr-ready-hygiene` | 184 | 49 versions | Standardized to canonical definition |
| `openai` | 57 | 57 versions | Standardized to canonical definition |
| `imgscore-backend-implementer` | 10 | 3 versions | Standardized to canonical definition |
| `imgscore-mcp-debug` | 10 | 3 versions | Standardized to canonical definition |
| `wsl-environment` | 10 | 3 versions | Standardized to canonical definition |
| `wsl-tf-python-runner` | 10 | 3 versions | Standardized to canonical definition |
| `gallery-electron-ts` | 6 | 4 versions | Standardized to canonical definition |
| `gallery-mcp-debug` | 6 | 3 versions | Standardized to canonical definition |
| `external-antigravity-review` | 4 | 2 versions | Standardized to canonical definition |
| `external-swarm` | 4 | 2 versions | Standardized to canonical definition |
| `video-electron-ts` | 4 | 4 versions | Standardized to canonical definition |
| `video-mcp-debug` | 4 | 4 versions | Standardized to canonical definition |
| `analyzer` | 2 | 1 versions | Standardized to canonical definition |
| `comparator` | 2 | 1 versions | Standardized to canonical definition |
| `grader` | 2 | 1 versions | Standardized to canonical definition |
| `code-simplifier` | 2 | 2 versions | Standardized to canonical definition |

---

## 6. MCP Servers Compendium

| Server Name | Instances | Scopes / Projects | Nature | Command / Transport |
|---|---|---|---|---|
| `accounting-debugger` | 3 | accounting | Project-Specific | `d:\Projects\accounting\venv\Scripts\python.exe` |
| `agent-mailbox` | 1 | mcp-agent-mailbox | Project-Specific | `stdio/inproc` |
| `agent-remote-control` | 1 | cursor-telegram-bot | Project-Specific | `node` |
| `birdweather` | 4 | birdweather-telegram-bot | Project-Specific | `node` |
| `burstpick-control` | 4 | burstpick-re | Project-Specific | `C:\Program Files\nodejs\node.exe` |
| `chrome-devtools` | 1 | user | Global / Core | `npx` |
| `cli-review` | 4 | video-gallery | Project-Specific | `node` |
| `code-review` | 1 | user | Global / Core | `cmd.exe` |
| `codex_app` | 1 | user | Global / Core | `cmd.exe` |
| `context7` | 1 | user | Global / Core | `stdio/inproc` |
| `cua_repl` | 1 | user | Global / Core | `C:\Users\dmnsy\AppData\Local\OpenAI\Codex\runtimes\cua_node\78fb63cda1a9e2b2\bin\node.exe` |
| `data-agent-kit` | 1 | user | Global / Core | `node` |
| `dh-synth-debug` | 3 | ddo-tools | Project-Specific | `stdio/inproc` |
| `discord` | 1 | user | Global / Core | `bun` |
| `docker-mcp` | 5 | user | Global / Core | `docker` |
| `electron` | 4 | burstpick-re | Project-Specific | `C:\Program Files\nodejs\npx.cmd` |
| `enshrouded-debug` | 4 | enshrouded-tools | Project-Specific | `python` |
| `everypixel-rw-labs` | 1 | everypixel-mcp | Project-Specific | `uv` |
| `fakechat` | 1 | user | Global / Core | `bun` |
| `fff-be` | 4 | image-scoring-backend | Project-Specific | `C:\Users\dmnsy\AppData\Local\fff-mcp\bin\fff-mcp.exe` |
| `finance` | 1 | user | Global / Core | `stdio/inproc` |
| `github` | 9 | user, warp | Global / Core | `npx` |
| `gmail` | 1 | user | Global / Core | `stdio/inproc` |
| `google-calendar` | 1 | user | Global / Core | `stdio/inproc` |
| `graphify` | 4 | heroes-templates | Project-Specific | `C:\Users\dmnsy\.local\bin\graphify-mcp.exe` |
| `graphify-be` | 4 | image-scoring-backend | Project-Specific | `C:\Users\dmnsy\.local\bin\graphify-mcp.exe` |
| `hetzner` | 1 | birdweather-telegram-bot | Project-Specific | `node` |
| `image-scoring-gallery-live` | 1 | user | Global / Core | `stdio/inproc` |
| `image-scoring-gallery-stdio` | 1 | user | Global / Core | `node` |
| `image-scoring-pipeline-postgres` | 1 | user | Global / Core | `D:\Projects\image-scoring-pipeline\tools\toolbox.exe` |
| `image-scoring-pipeline-stdio` | 1 | user | Global / Core | `python` |
| `image-scoring-pipeline-webui` | 1 | user | Global / Core | `stdio/inproc` |
| `imessage` | 1 | user | Global / Core | `bun` |
| `imgscore-py-postgres` | 2 | image-scoring, image-scoring-skills | Project-Specific | `cmd` |
| `imgscore-py-sse` | 3 | image-scoring, image-scoring-skills | Project-Specific | `stdio/inproc` |
| `imgscore-py-stdio` | 5 | image-scoring, image-scoring-skills | Project-Specific | `cmd` |
| `is-be-mcp` | 8 | image-scoring-backend, user | Global / Core | `node` |
| `jev-engineering` | 5 | user | Global / Core | `C:\Users\dmnsy\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.EXE` |
| `jev-rw-systemone` | 13 | image-scoring, jev-mcp, user | Global / Core | `uv` |
| `lightroom` | 4 | lightroom-mcp | Project-Specific | `d:\Projects\lightroom-mcp\mcp-server\.venv\Scripts\python.exe` |
| `lightroom-settings` | 2 | lightroom-mcp, lightroom-settings | Project-Specific | `python` |
| `llmwiki-ro-core` | 38 | image-scoring, image-scoring-backend, image-scoring-model (+5) | Global / Core | `uv` |
| `node_repl` | 1 | user | Global / Core | `C:\Users\dmnsy\AppData\Local\OpenAI\Codex\runtimes\cua_node\78fb63cda1a9e2b2\bin\node_repl.exe` |
| `notebooks` | 1 | user | Global / Core | `node` |
| `nwn-project` | 4 | nwn-modules | Project-Specific | `C:/Program Files/nodejs/node.exe` |
| `openaiDeveloperDocs` | 35 | chronix, everypixel-mcp, image-scoring (+7) | Global / Core | `stdio/inproc` |
| `pixellab` | 6 | heroes-templates, project-twelve, user | Global / Core | `stdio/inproc` |
| `proj-ro-graphify` | 5 | everypixel-mcp, synthet-code-framework | Project-Specific | `graphify-mcp` |
| `project-twelve-fff-mcp` | 6 | project-twelve, user | Global / Core | `C:\Users\dmnsy\AppData\Local\fff-mcp\bin\fff-mcp.exe` |
| `project-twelve-graphify-mcp` | 4 | project-twelve | Project-Specific | `node` |
| `project-twelve-ingame-mcp` | 6 | project-twelve, user | Global / Core | `stdio/inproc` |
| `project-twelve-unity-mcp` | 6 | project-twelve, user | Global / Core | `C:\Users\dmnsy\.unity\relay\relay_win.exe` |
| `rea` | 4 | burstpick-re | Project-Specific | `C:\Program Files\nodejs\node.exe` |
| `sqlite` | 9 | accounting, birdweather-telegram-bot | Project-Specific | `C:\Users\dmnsy\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts\mcp-server-sqlite.exe` |
| `subagent-orchestrator` | 5 | user | Global / Core | `node` |
| `synthet-agent-swarm` | 5 | user | Global / Core | `node` |
| `telegram` | 1 | user | Global / Core | `bun` |
| `unity-mcp` | 1 | user | Global / Core | `C:\Users\dmnsy\.unity/relay\relay_win.exe` |
| `unityMCP` | 1 | user | Global / Core | `stdio/inproc` |
| `video-gallery-live` | 4 | video-gallery | Project-Specific | `stdio/inproc` |
| `video-gallery-stdio` | 4 | video-gallery | Project-Specific | `node` |
| `visualization` | 1 | user | Global / Core | `node` |
| `win-gui-mcp` | 4 | win-gui-mcp | Project-Specific | `dotnet` |

---

## 7. Native Hooks Compendium

| Hook Group | Location / Context | Purpose |
|---|---|---|
| **Warp PowerShell Lifecycle Hooks** | `~/.claude/warp/*.ps1` | `on-prompt-submit`, `on-session-start`, `on-post-tool-use`, `on-permission-request`, `on-stop`, `on-stop-failure` |
| **Cursor Telegram Bot Hooks** | `.cursor/hooks/hook-policy.json` | `before-mcp-tool`, `before-shell`, `session-end` event monitoring |
| **Claude Security Hooks** | `claude-security/hooks/` | Pre-tool and post-tool execution security validation |
| **Hookify Automation Hooks** | `hookify/hooks/` | `userpromptsubmit`, `pretooluse`, `posttooluse`, `stop` event handlers |
| **Ralph Loop Stop Hook** | `ralph-loop/hooks/` | Iteration stop control script (`stop-hook.sh`) |

---

## 8. Deduplication & Harmonization Matrix

1. **Single Source of Truth**: All shareable skills are canonically authored in `.claude/skills/` within `synthet-code-framework` (or `vault`).
2. **Generated Mirrors**: `.cursor/` and `.agents/` are automatically generated using `scripts/sync_assistant_trees.py`. Never hand-edited.
3. **Global Harmonization**: Cursor (`~/.cursor/skills`), Codex (`~/.agents/skills`), Antigravity (`~/.gemini/config/skills`), Claude (`~/.claude/skills`), and Grok (`~/.grok/bundled/skills`) receive the unified library.
4. **Isolation Boundary**: Project-specific skills remain strictly inside their respective projects to preserve clean context windows and avoid namespace collisions.

