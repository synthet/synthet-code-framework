---
name: managing-python-dependencies
description: "Use when adding or changing Python packages, starting a Python project or notebook, or about to run `pip install`. Avoids global installs, follows the project's tooling, and confirms the right virtual environment is active."
capability: "Detect the project package manager and install Python dependencies through it"
side_effect_level: local_write
approval_required: false
requires_tools: "The package manager the project uses; see body"
output_schema: "Detected package manager, the command used and the active environment"
risk_class: medium
license: Apache-2.0
metadata:
  version: v2
  publisher: google
---

# Python Dependency Management Rule

> [!CAUTION]
>
> **BEFORE any `pip install`**: You MUST first detect the project's existing
> dependency manager and use it correctly. Do NOT override the project's
> established tooling.

> [!NOTE]
>
> **Pre-Flight Environment Check Bundling**: You MUST NOT run multiple
> sequential 1-line shell check commands (e.g. separate commands for python
> version, pyspark version, auth check, pip list). Combine all pre-flight
> environment and package availability probes into a single composite python
> one-liner or shell check step.
>
> Example composite probe:
>
> ```bash
> python3 -c "import sys, importlib.util; print(f'Python {sys.version.split()[0]}'); [(print(f'{pkg}: {__import__(pkg).__version__}') if importlib.util.find_spec(pkg) else print(f'{pkg}: not found')) for pkg in ['pyspark', 'google.cloud.bigquery']]"
> ```
>
> This bundling also applies to dependency manager detection; use a single `ls`
> or `find` command to check for all potential dependency manager configuration
> and lock files at once (e.g. `ls uv.lock poetry.lock Pipfile.lock
> requirements.txt pyproject.toml`).

## Dependency Manager Detection

Before installing ANY Python package, check the workspace for these files **in
priority order**:

1.  **Signal:** `uv.lock` or `pyproject.toml` with `[tool.uv]`
    *   **Tool:** **uv**
    *   **Install:** `uv add <package>`
    *   **Setup:** `uv sync`
2.  **Signal:** `pyproject.toml` with `[tool.poetry]`
    *   **Tool:** **Poetry**
    *   **Install:** `poetry add <package>`
    *   **Setup:** `poetry install`
3.  **Signal:** `Pipfile`
    *   **Tool:** **Pipenv**
    *   **Install:** `pipenv install <package>`
    *   **Setup:** `pipenv install`
4.  **Signal:** `environment.yml`
    *   **Tool:** **Conda**
    *   **Install:** `conda install <package>`
    *   **Setup:** `conda env create -f environment.yml`
5.  **Signal:** `requirements.txt` only
    *   **Tool:** **venv + pip**
    *   **Install:** `.venv/bin/pip install <package>`
    *   **Setup:** `.venv/bin/pip install -r requirements.txt`
6.  **Signal:** None of the above
    *   **Tool:** **venv + pip** (default)
    *   **Install:** `.venv/bin/pip install <package>`
    *   **Setup:** `.venv/bin/pip install -r requirements.txt`

## Default: venv + pip

If no dependency manager is detected, use **venv + pip + requirements.txt** as
the default:

```bash
# Initialize environment
python3 -m venv .venv

# Add dependencies
.venv/bin/pip install <package>

# Preserve state
.venv/bin/pip freeze > requirements.txt
```

**Rules for venv + pip workflow:**

-   Always use `.venv/bin/pip` or `.venv/bin/python` (explicit path).
-   After installing, run: `.venv/bin/pip freeze > requirements.txt`.
-   When setting up: `.venv/bin/pip install -r requirements.txt`.

## Prohibited

-   **NEVER** run `pip install` globally
-   **NEVER** override an existing dependency manager with a different one
