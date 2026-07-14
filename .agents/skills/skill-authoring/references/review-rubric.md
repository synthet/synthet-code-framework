# Skill review rubric

Use this rubric before accepting a new or materially edited first-party skill.

## 1. Trigger accuracy

Review the `description` as operational routing text, not marketing copy.

- **Pass:** Names the concrete user requests that should load the skill.
- **Pass:** Includes important synonyms and near-boundary phrases.
- **Pass:** Explains when this skill should win over adjacent skills.
- **Fail:** Says only what the skill is, without when to use it.
- **Fail:** Uses broad claims like "always use" without a bounded domain.

Suggested prompt set:

| Prompt type | Purpose |
|-------------|---------|
| direct hit | A normal request that should clearly trigger the skill. |
| synonym hit | Different wording that should still trigger the skill. |
| boundary miss | Similar-looking request that should use another skill or no skill. |

## 2. Progressive disclosure and deduplication

Keep the loaded `SKILL.md` focused on routing and procedure. Move expensive detail to resources.

- **Pass:** The body tells the agent what to do next in a small number of steps.
- **Pass:** Long examples, provider specifics, schemas, and troubleshooting tables live in `references/`.
- **Pass:** Deterministic or repetitive work is delegated to `scripts/` where practical.
- **Pass:** Existing repo policy is linked instead of copied into the skill.
- **Fail:** Every invocation must read long examples or unrelated provider sections.
- **Fail:** The skill repeats content already maintained in canonical repo docs.
- **Fail:** The same checklist appears in both `SKILL.md` and a reference with only wording changes.

## 3. Local fit and maintainability

External skills should be adapted, not copied verbatim.

- **Pass:** Paths, commands, safety gates, and generated mirrors match this repository.
- **Pass:** The skill cites or points to canonical local docs when those docs own the policy.
- **Pass:** New behavior has an owner path and verification path.
- **Fail:** Mentions tools, paths, or runtime assumptions this repo does not support.
- **Fail:** Bypasses `.claude/` as the canonical authoring source.

## 4. Safety and permissions

Skills are operational instructions. Review them as a supply-chain surface.

- **Pass:** Frontmatter honestly represents side effects, approvals, tools, and output shape.
- **Pass:** Remote writes, external exports, destructive actions, and secret handling are explicit.
- **Pass:** Instructions cannot be interpreted as permission to ignore repo or system policy.
- **Fail:** Hidden network calls, credential handling, broad shell execution, or vague auto-fix loops.
- **Fail:** Trigger text impersonates a trusted skill or understates risk.

## 5. Evaluation evidence

Match the evidence to the change size.

| Change size | Minimum evidence |
|-------------|------------------|
| typo or link fix | frontmatter/sync checks if generated assets changed |
| workflow edit | frontmatter/sync checks plus focused human review against this rubric |
| new skill or major rewrite | direct-hit, synonym-hit, and boundary-miss prompts plus focused tests/scripts where behavior is deterministic |
| generated-tree or validator change | unit tests covering the changed behavior |

## 6. Acceptance checklist

- [ ] Skill has a distinct purpose and does not duplicate an existing skill.
- [ ] `description` explains when to use the skill with realistic trigger terms.
- [ ] `SKILL.md` stays concise; detailed material is routed to targeted references.
- [ ] Duplicated guidance has been consolidated or replaced with links to canonical docs.
- [ ] Repo-specific commands and paths are correct.
- [ ] Frontmatter risk metadata matches actual behavior.
- [ ] Canonical `.claude/` files and generated mirrors are in sync.
- [ ] `.agent/SKILL_INVENTORY.md` is updated for new or material skill changes.
