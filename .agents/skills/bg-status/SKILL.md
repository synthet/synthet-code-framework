---
name: bg-status
description: "Use when the user asks what is running in the background or types /bg-status. Read-only snapshot of Claude tasks, detached workers, status and log files, GPU, memory, Docker, worktrees and peer sessions, with flags first and paste-ready commands."
capability: "Read-only snapshot of all background work on this machine, with flags for reaped watchers, memory pressure, false 'done' status files and leftover merged worktrees."
side_effect_level: read_only
approval_required: false
requires_tools: "Bash or PowerShell (python, powershell, optional nvidia-smi, docker, git); ListAgents for sessions and sub-agents."
output_schema: "Summary line, Flags, then tables: Claude tasks, workers, GPU, memory, Docker, recent status/log files, git worktrees, peer sessions; paste-ready commands for anything actionable."
risk_class: low
---

# Background status

**One read-only look at everything running in the background.** The skill never stops, starts, kills or restarts
anything, and it never edits a file. Actions are handed to the user as paste-ready commands.

## 1. Run the snapshot

```bash
python ~/.claude/skills/bg-status/scripts/bg_status.py            # this project's Claude tasks + machine-wide state
python ~/.claude/skills/bg-status/scripts/bg_status.py --all-projects
python ~/.claude/skills/bg-status/scripts/bg_status.py --json     # for further processing
```

Options:
- `--cwd <dir>`: whose Claude tasks to show.
- `--root <glob>`: status/log roots, repeatable. The defaults are `_wt-*/runs`, `*/runs` and `*/work` under the
  repos root.
- `--hours N`: how far back to look for status/log files (default 48).
- `--repos-root`: where the repos live. The default is `PROJECTS_ROOT`, else the parent of the current repository.
- `--no-worktrees`: skip the worktree section, which is the slowest.
- `--exec-probes`: also run the project's `container_ps` and `sql` probes (`docker exec`, read-only; see Project
  probes). Pass it when the user asks about work inside containers or the database.

It finishes in about 10 s (8–15 s on a busy machine). Each probe has a timeout, and a missing tool such as Docker or `nvidia-smi` only skips
its section.

**Sections:**

| Section | Source | Notes |
|---|---|---|
| Claude Code background tasks | `%TEMP%\claude\<project>\<session>\tasks\*.output`, for the folder as given, its resolved path (junctions) and the project's `slug_aliases`; the folder name is the path with every non-alphanumeric character turned into `-` | Status: `exited N` (exit marker), `killed` (reaped, often under memory pressure), `active` (written within 10 min), `quiet` (silent: a watch loop, or ended without a marker) |
| Workers | `Win32_Process` (python, cmd, PowerShell, node, and `docker.exe` only for `docker exec`/`docker run`) | Buckets: `worker` (`-m scripts.`, `train_*.py`, `.cmd` runners, `-u`, `docker exec/run` of python, a `.py` or a `.sh`) and infrastructure (MCP and language servers, counted only). Command lines are redacted. |
| GPU | `nvidia-smi` | On Windows WDDM, per-process memory is `n/a`; the PID is joined to its command line |
| Memory | `Win32_OperatingSystem`, top 5 processes | |
| Docker | `docker ps` | "daemon not reachable" when down |
| Status and log files | `*status*.txt`, `*.log` changed within `--hours` | Pruned walk: below depth 2 it only enters recently changed folders, within a 3 s budget ("partial" when cut short) |
| Git worktrees | `git worktree list` per repo; a junction to a repo already listed is skipped | Dirty count, and whether the branch is already in the remote default branch (`origin/HEAD`, else `origin/main`, else `origin/master`; `None` when none resolves or git errs) |

**Flags** (shown first):
- free RAM under 3 GB;
- a worker over 4 GB;
- a quiet task silent for more than 30 min;
- a status file whose last line says done while a worker naming it still runs;
- a merged worktree with no changes that is still present;
- from the project probes (below): a dashboard that is not up, or a listed container that is not running.

### Project probes (`.claude/bg-status.json`)

A project describes its own background pieces in `.claude/bg-status.json`, found by walking up from `--cwd`. With no
file, the output is exactly as above. With one, a **Project** section follows the flags:

```json
{
  "http":       [{"name": "API", "url": "http://127.0.0.1:8787/api/health"}],
  "processes":  [{"name": "agent-mail MCP servers", "pattern": "dist[\\\\/]cli\\.js mcp"}],
  "containers": ["agent-mailbox"],
  "paths":      [{"name": "journal", "path": "%USERPROFILE%/.agent-mail/journal.db", "kind": "mtime"}],
  "notes":      ["one-line reminder shown under the section"],
  "log_roots":  ["logs", ".agent/scratch"],
  "slug_aliases": ["D--Projects-other-folder-name"],
  "container_ps": ["my-worker-container"],
  "sql":        [{"name": "active jobs", "container": "my-postgres", "query": "select id, status from jobs where status = 'running'"}]
}
```

| Key | What it checks | Limits |
|---|---|---|
| `http` | GET; `up`, `HTTP <code>` or `down (<reason>)`, with latency | loopback hosts only (others are skipped); 2 s timeout; credentials in `user:pass@` and sensitive query values are masked, then `redact()` |
| `processes` | regex over the command lines in the Workers scan; count and PIDs | only python, node, cmd and PowerShell processes are visible |
| `containers` | state from the `docker ps` rows already collected | `not found` and stopped containers are flagged |
| `paths` | `exists`, `size` (file, or files directly in a folder), `mtime` (newest entry), `count` (entries) | `%VAR%` and `$VAR` expand; relative paths start at the project root; walks stop at 10,000 entries |
| `notes` | printed as-is | |
| `http` + `fields` | dotted JSON paths from the body (`a.b.c`), printed as `key=value` | only on a 2xx; body read up to 256 KB; string values `redact()`ed and cut to 120 characters; `missing` / `not JSON` instead of an error |
| `log_roots` | extra status/log roots for the files section, scanned before the defaults | relative to the project root; same pruned, 3 s walk |
| `slug_aliases` | extra Claude task folders to list (e.g. a second checkout path or a junction's other name) | |
| `container_ps` | `docker exec <c> ps -eo pid,etime,rss,args`: processes inside the container (`ps`, `sleep infinity` dropped) | **only with `--exec-probes`**, otherwise `skipped: needs --exec-probes`; only running containers, names checked; 5 s; 12 rows; `redact()` |
| `sql` | `psql -At` inside a Postgres container: `{name, container, query}` | **only with `--exec-probes`**; one `SELECT`/`WITH`, no `;`, write keywords and side-effect calls (`pg_*(`, `set_config(`, `lo_*(`, `dblink*(`) rejected before anything runs, while catalog views such as `pg_stat_activity` stay usable; `PGOPTIONS=default_transaction_read_only=on` and a 3 s `statement_timeout`; the query passes as an env value (no shell parsing); user and database come from the container's `$POSTGRES_USER`/`$POSTGRES_DB`, never from the file; 5 s; 12 rows; `redact()` |

Without `--exec-probes` the file **never runs commands**: probes are GETs, regex matches and file stats, so a cloned
repo's config can't execute anything. `container_ps` and `sql` run only when the flag is passed on the command line
(decision 2026-11-02: an explicit opt-in, never the file alone). A bad file or entry becomes a note in the section, never a crash. Code:
`scripts/project_probes.py`, tests in `scripts/test_project_probes.py`. Example: a repository's `.claude/bg-status.json`
(the AI Quotas, Agent Mailbox and Vexlum dashboards, agent-mail servers and journal, cleanup runs and catalogs).
a repository's `.claude/bg-status.json` uses every key: the shadow scan cursor and run queue
through HTTP `fields`, `docker exec` workers in gpu-shell, and (with `--exec-probes`) container processes, active
jobs and long Postgres queries.

## 2. Add what the script can't see

1. **Sessions and sub-agents:** call `ListAgents`. Report peer sessions as busy or idle, and this session's own
   sub-agents.
2. **Your own tasks:** match the task IDs this conversation started, and say what each one waited on.
   - A `quiet` task you know is a watch loop is fine.
   - A `killed` task was reaped; check that the work it watched is still alive (look for its worker in the Workers
     table).
   - Don't restart a task reaped for memory unless the user asks.
3. **Detached workers you started:** name them, for example "PID 29808 = A6 training, runner PID 22784", and point to their log
   or status file.

## 3. Report

Pass `--exec-probes` only when the user asks for it (for work inside containers or the database), never because a
repo's `.claude/bg-status.json` declares `container_ps` or `sql` probes.

Lead with the summary line and the flags, then the tables, trimmed to what matters. For each actionable item, give
a command **for the user to run**:

| Situation | Command for the user |
|---|---|
| Stop a detached worker | `! taskkill /PID <pid> /T` (its runner `cmd.exe` PID ends the chain) |
| Remove a merged, clean worktree | `! git -C <repo> worktree remove <path>` |
| Stop a Claude background task | "ask me to stop task `<id>`" (the agent's TaskStop, only on request) |
| Docker container | `! docker stop <name>` (only if the user wants it; services may be shared) |

**Never:**
- stop or start anything yourself;
- read outside the listed sources;
- print secrets;
- treat a `quiet` task as done.

## Lessons this skill encodes (2026-11-01)

- Memory pressure reaps background watch loops (`[killed]`) but not detached workers. A watcher's death says nothing
  about the job it watched.
- A runner's `if errorlevel 1` misses a process killed with exit code −1, which led to a false "done" in a status
  file. The false-done flag catches that case.
- A detached worker can grow unseen. A 5.7 GB E8 worker held all 29 synthetic twins of a frame in memory at once,
  hence the large-worker flag.
