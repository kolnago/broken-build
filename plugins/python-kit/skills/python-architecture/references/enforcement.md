# Enforcement: import-linter and CI

The dependency rule is a promise only if a tool checks it. Two contracts cover most projects;
name them after the principle they enforce so a failure reads as a rule citation.

```toml
# pyproject.toml
[tool.importlinter]
root_packages = ["<pkg>"]
include_external_packages = true

[[tool.importlinter.contracts]]
name = "core is framework-free (P2)"
type = "forbidden"
source_modules = ["<pkg>.core"]
forbidden_modules = [
  "fastapi", "jinja2", "sqlite3", "httpx", "google", "mcp",      # whatever the project uses outside core
  "<pkg>.data", "<pkg>.adapters", "<pkg>.web", "<pkg>.agents", "<pkg>.container",
]

[[tool.importlinter.contracts]]
name = "callers reach data and adapters only through the container (§3)"
type = "forbidden"
source_modules = ["<pkg>.web", "<pkg>.agents", "<pkg>.jobs", "<pkg>.tools", "<pkg>.workflows"]
forbidden_modules = ["<pkg>.data", "<pkg>.adapters"]
```

Layered projects can add a `layers` contract listing the packages from outside in; `forbidden`
contracts are easier to read in a failure and enough for two or three layers.

## No float for money

A grep is enough and runs in a second:

```bash
#!/usr/bin/env bash
# scripts/check_no_float.sh — fails when float or REAL appears where money lives
set -euo pipefail
! grep -rnE '\bfloat\b' src/<pkg>/core/ --include='*.py' | grep -v '# float-ok'
! grep -rnEi '\bREAL\b' src/<pkg>/data/migrations/ src/<pkg>/data/sql/
```

## Minimal CI, in the order that fails fastest

```
ruff check . && ruff format --check .
pyright                      # strict for <pkg>.core
lint-imports
scripts/check_no_float.sh
pytest                       # network disabled where the project says so
python <specfirst>/scripts/specfirst.py check
```

Run the same list locally as the definition of done. If CI minutes are scarce, one Linux job on
every push and the second platform only on pull requests keeps the allowance intact.
