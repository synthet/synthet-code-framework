---
name: agent-runtime-handoff
description: "Use when adopting agent scaffolding or handing specifications to an application runtime with tools, orchestration, evaluations and telemetry."
capability: "Use when adopting agent scaffolding or handing specifications to an application runtime with tools, orchestration, evaluations and telemetry."
side_effect_level: read_only
approval_required: false
requires_tools: "Project-documented tools; see body."
output_schema: "Evidence, changes and verification report."
risk_class: low
---

# agent runtime handoff

Separate editor instructions and workflows from executable application components. Skills/rules/commands guide the coding agent; the application owns orchestration, tools, schema validation, policy middleware, eval datasets, traces and MCP processes.
Identify runtime owners and existing dependencies from code. Close the handoff with where implementation, evaluation and telemetry live, verification evidence and rollback.
Do not treat installing Markdown as installing an agent runtime or prescribe a provider without a requirement.

## Spec layers

Name the layers in scope so specs, plans and runtime design stay aligned:

| Layer | Meaning | Usual owner |
|---|---|---|
| Contracts | Tool schemas, structured input and output, API shapes | Code and schema artifacts |
| Workflow | Graphs, steps, orchestration, checkpoints | Application code |
| Policy | Guardrails, allow and deny rules, data handling | Middleware, config, policy services |
| Test and eval | Datasets, rubrics, graders, regression suites | Tests, evaluation tools, CI |
| Ops | Traces, metrics, audit logs, alerting | Telemetry stack |
