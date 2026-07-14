---
name: skill-authoring
description: Use when creating, reviewing, or improving first-party agent skills in this repo. Apply whenever a user asks to add a skill, edit SKILL.md, review a skill diff, tune trigger descriptions, deduplicate skill guidance, add skill evals, or adapt patterns from Anthropic's public skills into the canonical .claude skill tree.
capability: "Create and improve repository agent skills with trigger-aware metadata, progressive disclosure, review rubrics, evals, and generated-tree sync."
side_effect_level: local_write
approval_required: false
requires_tools: "git, python, scripts/sync_assistant_trees.py, scripts/ci/check_agent_frontmatter.py; optional pytest for sync/frontmatter tests."
output_schema: "Skill patch or review report with sync/frontmatter/test summary and AST10 notes when applicable."
risk_class: medium
---

# Skill authoring

## Purpose

Create, review, and refine durable first-party skills. Keep `SKILL.md` as the compact routing and
workflow layer; move long checklists, examples, provider details, and deterministic helpers into
bundled resources.

This repo's source of truth is `.claude/skills/`. The `.cursor/skills/` and `.agents/skills/` trees
are generated mirrors and must not be edited by hand.

## When to Use

Use this skill when the task asks to:

- create, add, update, improve, consolidate, deduplicate, benchmark, or test a skill
- edit `SKILL.md`, skill frontmatter, bundled skill resources, or trigger descriptions
- review a skill diff for trigger accuracy, progressive disclosure, local fit, or safety
- port external skill examples into this repository without copying unsupported assumptions
- diagnose why a skill under-triggers, over-triggers, or causes noisy behavior

## Required Tools

- `git status --short` and bounded `git diff` commands
- `python scripts/sync_assistant_trees.py` and `python scripts/sync_assistant_trees.py --check`
- `python scripts/ci/check_agent_frontmatter.py`
- Optional: `pytest tests/test_sync_assistant_trees.py tests/test_agent_frontmatter.py`

## Workflow

1. **Review first.** For an existing skill or diff, apply
   [references/review-rubric.md](references/review-rubric.md) before editing.
2. **Choose the smallest scope.** Improve an existing skill when the workflow is adjacent; create a
   new skill only for a distinct trigger surface and procedure.
3. **Edit canonical assets only.** Change `.claude/skills/<name>/SKILL.md` and optional
   `.claude/skills/<name>/{references,scripts,assets}/...` resources.
4. **Deduplicate.** Keep quick routing/workflow in `SKILL.md`; move repeated, long, or variant-heavy
   guidance into targeted references. Do not duplicate policy already owned by repo docs.
5. **Sync mirrors.** Run `python scripts/sync_assistant_trees.py` after editing `.claude/` assets.
6. **Validate and summarize.** Run sync/frontmatter checks, focused tests when warranted, and note
   AST10 safety considerations for material skill changes.

## Authoring Rules of Thumb

- The `description` is the trigger surface: include what the skill does, when to use it, key
  synonyms, and near-boundary cases.
- Frontmatter must honestly represent side effects, approvals, required tools, output shape, and
  risk. Do not understate remote writes, external exports, destructive actions, or secret handling.
- Progressive disclosure matters: load only the next useful instructions by default, and point to a
  single relevant reference for deeper detail.
- External examples are inputs, not source-of-truth. Adapt paths, commands, permissions, and testing
  to this repo before committing.
- Use lightweight eval prompts for non-trivial skill changes: direct hit, synonym hit, and boundary
  miss. Add script/unit tests only for deterministic behavior.

## Verification Checklist

- [ ] Canonical source changed under `.claude/skills/`
- [ ] Detailed or repeated guidance moved to `references/`, `scripts/`, or `assets/` as appropriate
- [ ] Review rubric applied for new skills or material rewrites
- [ ] `python scripts/sync_assistant_trees.py` run after canonical edits
- [ ] `python scripts/sync_assistant_trees.py --check` passes
- [ ] `python scripts/ci/check_agent_frontmatter.py` passes
- [ ] `.agent/SKILL_INVENTORY.md` updated for new or materially changed skills
- [ ] AST10 review considerations documented in the PR summary for material changes
