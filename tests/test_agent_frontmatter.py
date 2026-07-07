from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "ci"
    / "check_agent_frontmatter.py"
)
spec = importlib.util.spec_from_file_location("check_agent_frontmatter", MODULE_PATH)
check_agent_frontmatter = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(check_agent_frontmatter)


def write_asset(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def run_check(root: Path) -> tuple[int, str]:
    errors: list[str] = []
    check_agent_frontmatter.check_skills(root, errors)
    check_agent_frontmatter.check_agents(root, errors)
    check_agent_frontmatter.check_commands(root, errors)
    return (1 if errors else 0), "\n".join(errors)


def skill_frontmatter(**overrides: str) -> str:
    values = {
        "name": "demo",
        "description": "Demo skill.",
        "capability": "Read repository context.",
        "side_effect_level": "read_only",
        "approval_required": "false",
        "requires_tools": "rg",
        "output_schema": "Markdown report.",
        "risk_class": "low",
    }
    values.update(overrides)
    lines = ["---", *(f"{k}: {v}" for k, v in values.items()), "---", "", "# Demo"]
    return "\n".join(lines) + "\n"


def command_frontmatter(**overrides: str) -> str:
    values = {
        "capability": "Read repository context.",
        "side_effect_level": "read_only",
        "approval_required": "false",
        "requires_tools": "rg",
        "output_schema": "Markdown report.",
        "risk_class": "low",
    }
    values.update(overrides)
    return "\n".join(
        [
            "---",
            *(f"{k}: {v}" for k, v in values.items()),
            "---",
            "",
            "# /demo — Demo",
            "",
        ]
    )


def test_valid_metadata_passes(tmp_path: Path) -> None:
    write_asset(tmp_path, ".claude/skills/demo/SKILL.md", skill_frontmatter())
    status, output = run_check(tmp_path)
    assert status == 0, output


def test_missing_metadata_fails(tmp_path: Path) -> None:
    write_asset(
        tmp_path,
        ".claude/skills/demo/SKILL.md",
        "---\nname: demo\ndescription: Demo skill.\n---\n\n# Demo\n",
    )
    status, output = run_check(tmp_path)
    assert status == 1
    assert "missing or empty `capability`" in output
    assert "missing or empty `risk_class`" in output


def test_invalid_enum_and_boolean_values_fail(tmp_path: Path) -> None:
    write_asset(
        tmp_path,
        ".claude/skills/demo/SKILL.md",
        skill_frontmatter(
            side_effect_level="network_magic",
            approval_required="sometimes",
            risk_class="critical",
        ),
    )
    status, output = run_check(tmp_path)
    assert status == 1
    assert "invalid `side_effect_level`" in output
    assert "`approval_required` must be boolean" in output
    assert "invalid `risk_class`" in output


def test_external_export_high_risk_assets_require_approval(tmp_path: Path) -> None:
    write_asset(
        tmp_path,
        ".claude/agents/external-codex-review.md",
        "\n".join(
            [
                "---",
                "name: external-codex-review",
                "description: External Codex review.",
                "capability: Send repository snippets to Codex for external review.",
                "side_effect_level: read_only",
                "approval_required: false",
                "requires_tools: subagent-orchestrator",
                "output_schema: Markdown findings.",
                "risk_class: high",
                "---",
                "",
                "# External Codex Review",
                "",
            ]
        ),
    )
    status, output = run_check(tmp_path)
    assert status == 1
    assert "require `side_effect_level: external_export`" in output
    assert "require `approval_required: true`" in output


def test_pr_issue_project_mutation_commands_require_remote_write(
    tmp_path: Path,
) -> None:
    write_asset(
        tmp_path,
        ".claude/commands/task-claim.md",
        command_frontmatter(capability="Assign issue and update project card.")
        + "gh issue edit 1 --add-assignee @me\ngh project item-edit --id X\n",
    )
    status, output = run_check(tmp_path)
    assert status == 1
    assert "mutation commands require `side_effect_level: remote_write`" in output
