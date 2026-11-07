---
description: "/constitution — Draft or refine stable project principles"
capability: "constitution agent asset workflow"
side_effect_level: local_write
approval_required: false
requires_tools: "See asset body for tool requirements."
output_schema: "Markdown report or documented command output."
risk_class: low
---

# /constitution — Project principles

Use to draft or refine the stable principles that specs and plans must respect. This sets direction; it does not replace `AGENTS.md`, which stays the operating contract.

## Inputs

- A new project, or the path to an existing principles file.
- Constraints from `AGENTS.md`, such as stack and boundaries.

## Output

1. **Purpose:** why the document exists.
2. **Principles:** short bullets that guide tradeoffs.
3. **Decision weights:** the order to apply when principles conflict.
4. **Non-negotiables:** what specs must not violate.
5. **Quality bar:** review, testing and evaluation expectations, as pointers.
6. **Review cadence:** when to revisit the document.

## Done when

The principles are concrete enough to judge a new spec or plan without debating the basics again.

Save the result where the project keeps its docs, and link it from `AGENTS.md`.
