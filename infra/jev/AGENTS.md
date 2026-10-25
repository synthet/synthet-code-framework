# Jev engineering

This checkout is the shared decision layer. Use `jev_decide`, `jev_route_task`, `jev_select_context`, and `jev_assess_risk`. Do not treat Jev as the coding model. Do not send secrets. A failed Jev call does not permit an action.

Tests: `uv sync --extra dev` then `.venv\Scripts\python.exe -m pytest`.
