"""stdio MCP tools for the engineering layer."""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from .service import Engineering

INSTRUCTIONS = (
    "Jev engineering returns typed routing, context, and risk decisions. "
    "It does not write code. jev_assess_risk never permits an action. "
    "Deterministic deny and ask rules win over Jev. Do not send secrets."
)
ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=True,
)


def create_server(service: Engineering | None = None) -> MCPServer:
    engineering = service or Engineering()
    mcp = MCPServer("jev-engineering", version="0.1.0", instructions=INSTRUCTIONS)

    @mcp.tool(annotations=ANNOTATIONS)
    async def jev_decide(task: str, has_defaults: bool = False) -> dict[str, Any]:
        """Classify a coding task with one batched Jev request."""
        return engineering.decide(task, has_defaults=has_defaults)

    @mcp.tool(annotations=ANNOTATIONS)
    async def jev_route_task(
        task: str,
        current_model: str = "opus",
        context_tokens: int = 0,
        output_tokens: int = 0,
        read_tokens: int = 0,
        has_defaults: bool = False,
    ) -> dict[str, Any]:
        """Recommend a model at a task boundary. Does not change harness settings."""
        return engineering.route_task(
            task,
            current_model=current_model,
            context_tokens=context_tokens,
            output_tokens=output_tokens,
            read_tokens=read_tokens,
            has_defaults=has_defaults,
        )

    @mcp.tool(annotations=ANNOTATIONS)
    async def jev_select_context(query: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Score evidence chunks and return hide, short, long, or full visibility."""
        return engineering.select_context(query, chunks, live=True)

    @mcp.tool(annotations=ANNOTATIONS)
    async def jev_assess_risk(
        command: str = "",
        paths: list[str] | None = None,
        extra: str = "",
        tool_name: str = "",
    ) -> dict[str, Any]:
        """Advisory risk check. Returns deny, ask, or defer, never allow."""
        return engineering.assess_risk(
            command=command, paths=paths, extra=extra, tool_name=tool_name, live=True,
        )

    return mcp


def run_stdio(service: Engineering | None = None) -> None:
    create_server(service).run(transport="stdio")
