---
name: accidental-data-loss-prevention
description: "Use before any command that irreversibly destroys data: SQL DROP, TRUNCATE or broad DELETE, deleting cloud storage, projects, secrets or keys. Stop and get explicit user consent first."
capability: "Halt irreversible data-loss commands until the user gives explicit consent"
side_effect_level: read_only
approval_required: true
requires_tools: "None; applies to whichever tool would run the destructive command"
output_schema: "Impact statement, reason and an explicit consent request before any destructive action"
risk_class: high
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

# Accidental Data Loss Prevention

> [!CAUTION]
>
> **STOP AND VERIFY**: Before running any command or tool that results in
> irreversible data loss, you **MUST** obtain explicit user consent.

## Mandatory Procedure

1.  **Halt Execution**: Do **not** execute the command.
2.  **Request Consent**: Explain clearly to the user:
    -   The **impact** of this deletion.
    -   **Why** you believe this is necessary.
    -   A request for their **explicit approval** to proceed.
3.  **Wait**: Only proceed if the user provides clear, affirmative consent in
    the conversation.
