---
name: mcp-server-design
description: Use when designing, building, reviewing, or extending a Model Context Protocol server: tools, resources, prompts, transports, input validation, auth, and safe dispatch surfaces. Trigger on MCP server design, agent tool integration, tool schemas, or MCP security review.
capability: "mcp-server-design agent asset workflow"
side_effect_level: local_write
approval_required: false
requires_tools: "See asset body for tool requirements."
output_schema: "Markdown report or documented command output."
risk_class: medium
---

# MCP server design

## Quick start

Use this skill when a change exposes project capabilities to AI agents through MCP:

- Creating or extending an MCP server
- Adding tools, resources, prompts, or server configuration
- Reviewing tool schemas, transport/auth, or side-effect safety
- Configuring `.cursor/mcp.example.json`, `.mcp.json`, or Codex MCP entries

## Design workflow

1. Read the [MCP specification](https://modelcontextprotocol.io/specification) and the SDK docs for
   the language/runtime you are using.
2. Pick a clear, stable **server name** and tool names (`<scope>_<verb>`, e.g. `db_query`).
3. **Transport:** stdio by default for local tools. Use explicit auth for remote transports.
4. **Secrets:** pass secrets through environment variables or secret stores; never CLI args.
5. **Tools:** validate every input with a schema (Zod, pydantic, JSON Schema, etc.). Prefer a compact
   surface (a `search` + `dispatch` pair) over dozens of raw tools when the domain is large.
6. **Separate read from write.** Read-only tools are safe-by-default; **write/side-effecting tools**
   must require explicit confirmation (e.g. a `confirmed: true` flag and an allowlist of actions).
7. **Resources:** expose read-only context (status, schema, recent events). Do not expose secrets.
8. **Prompts:** ship reusable prompt templates for common workflows where helpful.
9. On downstream/dependency failure, return **structured diagnostics** instead of opaque errors.
10. Test handlers with mocked dependencies; unit tests must not perform live side effects.

## Tool contract checklist

For each tool, document:

- Purpose and expected user intent
- Input schema and validation failures
- Output shape, including error/diagnostic fields
- Side-effect level (`read_only`, `local_write`, `remote_write`, or `external_export`)
- Confirmation requirements and allowlisted actions for writes
- Secret-handling boundaries and log redaction

## Safety checks

- No raw shell / file / network / arbitrary-code tools without an explicit approval policy.
- All tool inputs validated against a schema.
- Side-effecting tools gated behind confirmation + allowlist; destructive actions need a written
  authorization path. See [.agent/SAFETY.md](../../../.agent/SAFETY.md).
- Remote transports must have authentication, authorization, and rate/resource limits.
- Tool responses must not include credentials, hidden prompts, environment dumps, or unbounded logs.

## Done criteria

- Tool list matches the published schemas; descriptions are accurate and current.
- Secrets only via env; never logged or returned in tool output.
- Build produces the server entrypoint referenced by your MCP config.
- Tests cover validation failures, permission failures, and happy paths.
- An inventory/reference doc is regenerated when the tool set changes.

References: [MCP docs](https://modelcontextprotocol.io), Cursor / Claude Code MCP configuration guides.
