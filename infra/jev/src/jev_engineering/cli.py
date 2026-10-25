"""Command line for routing cards and the MCP server."""

from __future__ import annotations

import argparse
import json
import sys

from .service import Engineering


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jev-engineering")
    sub = parser.add_subparsers(dest="command", required=True)

    route = sub.add_parser("route")
    route.add_argument("--task", required=True)
    route.add_argument("--current-model", default="opus")
    route.add_argument("--context-tokens", type=int, default=0)
    route.add_argument("--output-tokens", type=int, default=0)
    route.add_argument("--read-tokens", type=int, default=0)

    decide = sub.add_parser("decide")
    decide.add_argument("--task", required=True)

    sub.add_parser("catalog")
    sub.add_parser("mcp")

    args = parser.parse_args(argv)
    if args.command == "mcp":
        from .mcp_server import run_stdio

        run_stdio()
        return 0
    engineering = Engineering()
    if args.command == "route":
        payload = engineering.route_task(
            args.task,
            current_model=args.current_model,
            context_tokens=args.context_tokens,
            output_tokens=args.output_tokens,
            read_tokens=args.read_tokens,
        )
    elif args.command == "decide":
        payload = engineering.decide(args.task)
    else:
        payload = engineering.capabilities(include_schema=False)
    json.dump(_card(payload), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _card(payload: dict) -> dict:
    hidden = {"instructions"}
    return {key: value for key, value in payload.items() if key not in hidden}


if __name__ == "__main__":
    raise SystemExit(main())
