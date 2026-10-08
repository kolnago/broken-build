# Configuration for the module shape

Fragments to paste into a new repository. `target-version`, `requires-python` and `fail_under`
are opinions; set them to what the deployment platform and `google-adk` support.

## pyproject.toml

```toml
[project]
name = "risk-agent"
requires-python = ">=3.12"
dependencies = ["google-adk>=2.11,<3", "pydantic>=2.7,<3", "pydantic-settings>=2,<3", "structlog>=24"]

[dependency-groups]
dev = ["pytest", "pytest-asyncio", "pytest-cov", "hypothesis", "mypy", "ruff", "import-linter", "pip-audit"]

[tool.uv]
package = true          # installs the repository, so `modules` imports work under `adk web` too

[tool.setuptools]
packages = { find = { include = ["modules*", "apps*"] } }

# ----- the charter --------------------------------------------------------------------------

[tool.adk_modules]      # read by scripts/check_modules.py (charter M3)
order = [
  ["breaches.*"],
  ["investigation"],
  ["exposure"],
]

[tool.importlinter]     # the same order, checked on the installed package
root_packages = ["modules", "apps"]

[[tool.importlinter.contracts]]
name = "Modules import downward only (M3)"
type = "layers"
layers = [
  "modules.breaches",
  "modules.investigation",
  "modules.exposure",
]

[[tool.importlinter.contracts]]
name = "Breach types are independent (M3, M5)"
type = "independence"
modules = ["modules.breaches.limit_overdraft", "modules.breaches.collateral_shortfall"]

[[tool.importlinter.contracts]]
name = "Kinds import inward (M4)"
type = "layers"
containers = ["modules.exposure", "modules.investigation", "modules.breaches.limit_overdraft"]
layers = [            # coarser than check_modules.py, which holds the exact kind table:
  "agents | workflows | mcp",   # a tool may import a surface, so tools sit above it
  "tools",
  "surfaces | callbacks | skills",
  "calc | ports | fakes",
  "models",
]
exhaustive = false
# a brick's test may import its owner agent (skill recipe); name such imports here in full:
# ignore_imports = ["modules.orders.skills.order_terms.test_order_terms -> modules.orders.agents.analyst"]

[[tool.importlinter.contracts]]
name = "Nothing imports spikes"
type = "forbidden"
source_modules = ["modules", "apps"]
forbidden_modules = ["spikes"]

# ----- the Python rules ---------------------------------------------------------------------

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["ALL"]
ignore = [
  "D",       # docstrings enforced by review (python-rules §6)
  "COM812",  # conflicts with formatter
  "ISC001",  # conflicts with formatter
]

[tool.ruff.lint.per-file-ignores]
"**/test_*.py" = ["S101", "PLR2004", "ANN"]   # asserts, magic numbers, annotations in tests
"**/agent.py" = ["PLW0603"]                   # root_agent at module level is what adk needs
"spikes/**" = ["ALL"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]
warn_unreachable = true
files = ["modules", "apps", "scripts"]
exclude = ["spikes/"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true

[tool.pytest.ini_options]
addopts = "-q --strict-markers --strict-config -p no:cacheprovider"
testpaths = ["modules", "apps"]
asyncio_mode = "auto"
xfail_strict = true
filterwarnings = ["error"]

[tool.coverage.run]
branch = true
source = ["modules"]
omit = ["**/agent.py", "**/__main__.py"]   # entry points: wiring only (B7)

[tool.coverage.report]
fail_under = 85
show_missing = true
```

Keep the import-linter `layers` and `independence` lists in step with `[tool.adk_modules]
order`: a new module is added to both in the commit that creates it. `check_modules.py` reads
the order from the source tree, import-linter from the installed package; the two overlap on
purpose, so a mistake in one is caught by the other.

## StrictModel

```python
# modules/<module>/models/<name>/<name>.py, or a shared base in the bottom module of the order
from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",             # unknown fields are a bug, not noise
        frozen=True,                # models are values; mutate by .model_copy(update=...)
        str_strip_whitespace=True,
    )
```

## Makefile

```make
.PHONY: install lint format typecheck test modules audit check
install:   ; uv sync --all-groups
lint:      ; uv run ruff check . && uv run ruff format --check . && uv run lint-imports
format:    ; uv run ruff format . && uv run ruff check --fix .
typecheck: ; uv run mypy
test:      ; uv run pytest --cov --cov-report=term-missing
modules:   ; uv run python scripts/check_modules.py
audit:     ; uv run pip-audit
check: lint typecheck modules test audit
```

## .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks: [{ id: ruff, args: [--fix] }, { id: ruff-format }]
  - repo: local
    hooks:
      - { id: mypy, name: mypy, entry: uv run mypy, language: system, pass_filenames: false }
      - { id: lint-imports, name: lint-imports, entry: uv run lint-imports, language: system, pass_filenames: false }
      - { id: check-modules, name: check_modules, entry: uv run python scripts/check_modules.py, language: system, pass_filenames: false }
```

## Skeleton

```
.
├── pyproject.toml
├── uv.lock
├── .python-version
├── .pre-commit-config.yaml
├── Makefile
├── AGENTS.md                 "follows the adk-modules charter and its python-rules"
├── docs/decisions/           when the project does not use specfirst
├── modules/                  the charter's repository shape
├── apps/
├── spikes/
└── scripts/check_modules.py
```
