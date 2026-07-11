from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.detect_commands import detect_commands  # noqa: E402


def write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    ("signal", "expected_build", "expected_test", "expected_lint"),
    [
        ("uv.lock", "uv sync", "uv run pytest", "uv run ruff check . && uv run mypy ."),
        ("poetry.lock", "poetry install", "poetry run pytest", "poetry run ruff check . && poetry run mypy ."),
        ("pyproject-build-backend", "pip install -e .", "python -m pytest", "ruff check . && mypy ."),
        ("ruff.toml", "pip install -e .", "python -m pytest", "ruff check . && mypy ."),
        ("mypy.ini", "pip install -e .", "python -m pytest", "ruff check . && mypy ."),
        ("pytest.ini", "pip install -e .", "python -m pytest", "ruff check . && mypy ."),
    ],
)
def test_detect_python_supported_signals(
    tmp_path: Path,
    signal: str,
    expected_build: str,
    expected_test: str,
    expected_lint: str,
) -> None:
    write(
        tmp_path / "pyproject.toml",
        '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n[tool.ruff]\n[tool.mypy]\n',
    )
    write(tmp_path / "pytest.ini", "[pytest]\n")
    write(tmp_path / "ruff.toml", "line-length = 100\n")
    write(tmp_path / "mypy.ini", "[mypy]\n")
    if signal in {"uv.lock", "poetry.lock"}:
        write(tmp_path / signal)

    detected = detect_commands(tmp_path, "python")

    assert detected["BUILD_CMD"] == expected_build
    assert detected["TEST_CMD"] == expected_test
    assert detected["LINT_CMD"] == expected_lint


@pytest.mark.parametrize(
    ("lockfile", "expected_build", "expected_test", "expected_lint"),
    [
        ("package-lock.json", "npm run build", "npm test", "npm run lint"),
        ("pnpm-lock.yaml", "pnpm run build", "pnpm run test", "pnpm run lint"),
        ("yarn.lock", "yarn run build", "yarn run test", "yarn run lint"),
        ("bun.lockb", "bun run build", "bun run test", "bun run lint"),
        ("turbo.json", "npm run build", "npm test", "npm run lint"),
        ("nx.json", "npm run build", "npm test", "npm run lint"),
    ],
)
def test_detect_node_supported_signals(
    tmp_path: Path,
    lockfile: str,
    expected_build: str,
    expected_test: str,
    expected_lint: str,
) -> None:
    write(
        tmp_path / "package.json",
        '{"scripts":{"build":"vite build","test":"vitest run","lint":"eslint ."}}\n',
    )
    write(tmp_path / lockfile, "{}\n")

    detected = detect_commands(tmp_path, "node")

    assert detected["BUILD_CMD"] == expected_build
    assert detected["TEST_CMD"] == expected_test
    assert detected["LINT_CMD"] == expected_lint


def test_detect_node_uses_most_specific_lockfile_and_existing_scripts(tmp_path: Path) -> None:
    write(tmp_path / "package.json", '{"scripts":{"test":"vitest run","typecheck":"tsc --noEmit"}}\n')
    write(tmp_path / "package-lock.json", "{}\n")
    write(tmp_path / "pnpm-lock.yaml", "lockfileVersion: '9.0'\n")

    detected = detect_commands(tmp_path, "node")

    assert detected == {
        "BUILD_CMD": "pnpm install",
        "TEST_CMD": "pnpm run test",
        "LINT_CMD": "pnpm run typecheck",
    }


@pytest.mark.parametrize(
    ("filename", "contents", "expected"),
    [
        ("Makefile", "build:\n\ttouch build\ntest:\n\ttouch test\nlint:\n\ttouch lint\n", {"BUILD_CMD": "make build", "TEST_CMD": "make test", "LINT_CMD": "make lint"}),
        ("justfile", "build:\n  echo build\ntest:\n  echo test\nlint:\n  echo lint\n", {"BUILD_CMD": "just build", "TEST_CMD": "just test", "LINT_CMD": "just lint"}),
        ("Taskfile.yml", "version: '3'\ntasks:\n  build:\n    cmds: ['echo build']\n  test:\n    cmds: ['echo test']\n  lint:\n    cmds: ['echo lint']\n", {"BUILD_CMD": "task build", "TEST_CMD": "task test", "LINT_CMD": "task lint"}),
        (".mise.toml", "[tasks.build]\nrun = 'echo build'\n[tasks.test]\nrun = 'echo test'\n[tasks.lint]\nrun = 'echo lint'\n", {"BUILD_CMD": "mise run build", "TEST_CMD": "mise run test", "LINT_CMD": "mise run lint"}),
    ],
)
def test_detect_generic_supported_signals(tmp_path: Path, filename: str, contents: str, expected: dict[str, str]) -> None:
    write(tmp_path / filename, contents)

    assert detect_commands(tmp_path, "generic") == expected
