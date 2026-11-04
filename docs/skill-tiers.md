---
type: Reference
title: Skill Tiers
description: Where agent skills live, how same-name skills resolve per harness, and how the installer retires repository copies.
resource: skill-tiers.md
tags: [agents, skills, setup]
timestamp: 2026-11-03T00:00:00Z
okf_version: 0.1
---

# Skill tiers

Each skill has one home. Shared skills live at user level, and a repository holds only what is specific to it.

| Tier | Location | Contains | Manifest entry |
|---|---|---|---|
| User/global | `~/.claude/skills`, `~/.agents/skills`, `~/.gemini/config/skills`, `~/.gemini/antigravity-cli/skills` | Stack-neutral workflow and machine skills | `global: true`, `projects: []` |
| Stack pack | Repository `.claude/skills` and `.agents/skills` | Skills tied to a stack, for repositories that opt in | `global: false`, `projects: [...]` |
| Project-owned | Repository `.claude/skills` and `.agents/skills` | Skills about that repository | None |
| Provider-managed | `~/.claude/skills/synced`, `.codex/.system`, `.cursor/skills-cursor`, Gemini bundles, plugin caches | Owned by the provider, never edited | None |

[`library.json`](../.agent/setup/library.json) is the only source of tier assignments. A `pack: core` entry still installs into every repository, but the library no longer uses it.

## Why a project skill must not reuse a global name

| Harness | Same-name behaviour |
|---|---|
| Claude Code | Personal wins over project, so the repository copy never loads |
| Codex | Both appear; they are not merged |
| Cursor | Not documented. It also reads the Claude and Codex skill folders |

Name project skills with a project prefix, such as `imgscore-` or `enshrouded-`. The planner reports a `tier-collision` diagnostic for any kept repository skill that shares a global name.

## Command aliases

Skill aliases carry commands to harnesses that have no command concept.

- `framework-<command>` aliases exist at user level only.
- A repository gets a `project-<command>` alias only for a command it owns or has changed.

## Retiring repository copies

`plan` deletes a retired skill from a repository only when every guard passes:

1. The repository has an ownership ledger.
2. The repository is a Git checkout, so references can be searched.
3. Every file in the skill bundle matches the ledger, ignoring line endings and Python caches.
4. No tracked or untracked file outside retiring skills references `skills/<name>/`.
5. The bundle holds no file name the installer may not touch, such as `config.json`.

If any copy fails, the skill stays in every harness tree, and the plan reports why: `tier-collision` when it shares a global name, otherwise `tier-review`. To resolve one, rename it as a project skill, move its changes into the library, or remove it by hand.

Refresh the user tier before pruning repositories, because repositories then rely on those copies. Deleted files are restored by `rollback` from the receipt's backups.

Removing a repository's copy makes its Codex disable entry stale. The next global `plan` drops entries whose path under the projects root no longer exists.

## Trade-off

A clone on a machine without the user tier has only its stack-pack and project-owned skills.
