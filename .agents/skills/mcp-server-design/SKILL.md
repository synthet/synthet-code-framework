---
name: mcp-server-design
description: Use when designing, building, reviewing, or extending a Model Context Protocol server, including tools, resources, prompts, transports, input validation, auth, and safe dispatch surfaces. Always apply when the user mentions MCP server design or agent integration tools.
capability: "mcp-server-design agent asset workflow"
side_effect_level: local_write
approval_required: false
requires_tools: "See asset body for tool requirements."
output_schema: "Markdown report or documented command output."
risk_class: medium
---

# MCP server design

## Use this skill when

- Creating or extending an MCP server that exposes this project to AI agents
- Adding tools, resources, or prompts
- Configuring `.cursor/mcp.example.json` / `.mcp.json`

## Procedure

1. Read the [MCP specification](https://modelcontextprotocol.io/specification) and your SDK's docs.
2. Pick a clear, stable **server name** and a tool-naming scheme (`<scope>_<verb>`, e.g. `db_query`).
3. **Transport:** stdio by default; pass secrets via **environment variables**, never CLI args.
4. **Tools** — validate every input with a schema (e.g. Zod / pydantic). Prefer a small, compact
   surface (a `search` + `dispatch` pair) over dozens of raw tools when the domain is large.
5. **Separate read from write.** Read-only tools are safe-by-default; **write/side-effecting tools**
   must require explicit confirmation (e.g. a `confirmed: true` flag and an allowlist of actions).
6. **Resources** — expose read-only context (status, schema, recent events) — **no secrets**.
7. **Prompts** — ship reusable prompt templates for common workflows where helpful.
8. On a downstream/dependency failure: return **structured diagnostics**, do not throw opaque errors.
9. Test tool handlers with mocked dependencies (no live side effects in unit tests).

## Safety checks

- No raw shell / file / network / arbitrary-code tools without an explicit approval policy.
- All tool inputs validated against a schema.
- Side-effecting tools gated behind confirmation + allowlist; destructive actions need a written
  authorization path. See [.agent/SAFETY.md](../../../.agent/SAFETY.md).

## Done criteria

- Tool list matches the published schemas; descriptions are accurate and current.
- Secrets only via env; never logged or returned in tool output.
- Build produces the server entrypoint referenced by your MCP config.
- An inventory/reference doc is regenerated when the tool set changes.

References: [MCP docs](https://modelcontextprotocol.io), Cursor / Claude Code MCP configuration guides.
