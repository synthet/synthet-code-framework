#!/usr/bin/env python3
"""Generate starter boilerplate for bootstrapped projects.

This intentionally creates small, dependency-light defaults that make a newly
seeded repository runnable before the owner replaces the example app code.
"""

from __future__ import annotations

import argparse
from pathlib import Path

SUPPORTED_STACKS = ("python", "node", "go")


def _write(path: Path, content: str, *, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def generate_python(target: Path, project_slug: str, *, force: bool = False) -> list[Path]:
    package = project_slug.replace("-", "_")
    files = {
        Path("pyproject.toml"): f"""[build-system]\nrequires = [\"setuptools>=68\"]\nbuild-backend = \"setuptools.build_meta\"\n\n[project]\nname = \"{project_slug}\"\nversion = \"0.1.0\"\ndescription = \"TODO(PROJECT_DESC)\"\nrequires-python = \">=3.11\"\n\n[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n\n[tool.ruff]\nline-length = 100\n""",
        Path("src") / package / "__init__.py": "\"\"\"Project package.\"\"\"\n\n__all__ = [\"hello\"]\n\n\ndef hello() -> str:\n    return \"hello from {project_slug}\"\n".replace("{project_slug}", project_slug),
        Path("tests") / "test_smoke.py": f"""from {package} import hello\n\n\ndef test_hello() -> None:\n    assert hello() == \"hello from {project_slug}\"\n""",
    }
    return [target / rel for rel, content in files.items() if _write(target / rel, content, force=force)]


def generate_node(target: Path, project_slug: str, *, force: bool = False) -> list[Path]:
    files = {
        Path("package.json"): f"""{{\n  \"name\": \"{project_slug}\",\n  \"version\": \"0.1.0\",\n  \"private\": true,\n  \"type\": \"module\",\n  \"scripts\": {{\n    \"build\": \"tsc --noEmit\",\n    \"lint\": \"tsc --noEmit\",\n    \"test\": \"node --test\"\n  }},\n  \"devDependencies\": {{\n    \"typescript\": \"^5.0.0\"\n  }}\n}}\n""",
        Path("tsconfig.json"): """{\n  \"compilerOptions\": {\n    \"target\": \"ES2022\",\n    \"module\": \"NodeNext\",\n    \"moduleResolution\": \"NodeNext\",\n    \"strict\": true,\n    \"noEmit\": true\n  },\n  \"include\": [\"src/**/*.ts\"]\n}\n""",
        Path("src") / "index.ts": f"""export function hello(): string {{\n  return \"hello from {project_slug}\";\n}}\n""",
        Path("test") / "smoke.test.mjs": f"""import assert from 'node:assert/strict';\nimport test from 'node:test';\n\ntest('hello placeholder', () => {{\n  assert.equal('hello from {project_slug}', 'hello from {project_slug}');\n}});\n""",
    }
    return [target / rel for rel, content in files.items() if _write(target / rel, content, force=force)]


def generate_go(target: Path, project_slug: str, *, force: bool = False) -> list[Path]:
    module = project_slug.replace("-", "")
    files = {
        Path("go.mod"): f"module {module}\n\ngo 1.22\n",
        Path("main.go"): f"""package main\n\nimport \"fmt\"\n\nfunc Greeting() string {{\n\treturn \"hello from {project_slug}\"\n}}\n\nfunc main() {{\n\tfmt.Println(Greeting())\n}}\n""",
        Path("main_test.go"): f"""package main\n\nimport \"testing\"\n\nfunc TestGreeting(t *testing.T) {{\n\tif got := Greeting(); got != \"hello from {project_slug}\" {{\n\t\tt.Fatalf(\"Greeting() = %q\", got)\n\t}}\n}}\n""",
    }
    return [target / rel for rel, content in files.items() if _write(target / rel, content, force=force)]


def generate_boilerplate(target: Path, stack: str, project_slug: str, *, force: bool = False) -> list[Path]:
    generators = {"python": generate_python, "node": generate_node, "go": generate_go}
    generator = generators.get(stack)
    if generator is None:
        return []
    return generator(target, project_slug, force=force)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate starter project boilerplate")
    parser.add_argument("--target", type=Path, default=Path("."), help="Project root to write into")
    parser.add_argument("--stack", required=True, choices=SUPPORTED_STACKS, help="Boilerplate stack")
    parser.add_argument("--project-slug", required=True, help="Project/package slug")
    parser.add_argument("--force", action="store_true", help="Overwrite existing boilerplate files")
    args = parser.parse_args()

    written = generate_boilerplate(args.target.resolve(), args.stack, args.project_slug, force=args.force)
    if not written:
        print(f"No boilerplate written for stack {args.stack}.")
    else:
        print("Generated boilerplate files:")
        for path in written:
            print(f"  {path.relative_to(args.target.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
