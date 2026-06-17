---
type: Technical Reference
title: Security Model
description: Security model, secret-handling rules, and the pre-merge security review checklist.
resource: security.md
tags: [docs, security]
timestamp: 2026-06-16T00:00:00Z
okf_version: 0.1
---

# Security

## Secrets

- Secrets live in `secrets.json` / `.env` (git-ignored), never in committed config or code.
- Use `.env.example` for non-secret defaults.
- Secrets never appear in logs, tool output, audit logs, or external-review payloads.

## Hard rules

- Validate every external input against a schema; reject malformed payloads (fail-closed).
- Write/side-effecting operations require explicit confirmation and an allowlist.
- No raw shell / arbitrary-code tools without an approval policy.
- Never modify `.git/config` (see [`../.agent/SAFETY.md`](../.agent/SAFETY.md)).

## Review checklist (pre-merge)

- [ ] No secrets, tokens, or credentials in the diff.
- [ ] New inputs validated; injection/path-traversal considered.
- [ ] No new undocumented network calls or secret-storage locations.
- [ ] Side-effecting actions gated behind confirmation/approval.
- [ ] Logs/outputs redact sensitive values.

For new features touching MCP/tools/hooks/remote surfaces, run the
[`threat-modeling-agentic-tools`](../.claude/skills/threat-modeling-agentic-tools/SKILL.md) skill.
