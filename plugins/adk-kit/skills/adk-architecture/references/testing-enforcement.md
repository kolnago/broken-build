# ADK architecture guide v2.0 — §13–14 Testing strategy and enforcement (import-linter, CI)

Part of the guide split by section. Rule summary and file index: [../SKILL.md](../SKILL.md); overview, principles and layers: [overview.md](overview.md).

---

## 13. Testing strategy

| Target | Test type | Cloud | Proves |
|---|---|---|---|
| `core/calc` incl. `derive` | Unit, golden, property-based | No | Numbers correct and stable |
| `core/services` | Unit with fakes | No | Orchestration, entitlements, error mapping |
| `core/guardrails/numbers` | Unit with adversarial answers | No | Invented and computed numbers are caught; honest restatements pass |
| `data/` | Integration on a test dataset; dry-run of every `.sql` | Yes | Queries valid, parameterised, correct shape |
| Shell nodes | Unit with a stubbed agent node | No | Pass, retry, fallback routes; ledger reset per turn |
| Tools | Contract: schema snapshot, docstring present, error shape, JSON safety, ledger written | No | Model-facing contract does not drift |
| Agent | ADK evaluation sets | Model | Tool choice, multi-tool reasoning, verification pass rate, flag consistency |

- **TEST-1** No test asserts on a number produced by an LLM. Evals assert on tool choice, cited figures, pass rate, and flag consistency.
- **TEST-2** Property examples: `breached` ⇔ utilization > 1; `headroom + exposure == limit`; `derive.difference(a, b)` grounds only when `a` and `b` are in the ledger.
- **TEST-3** Consistency evals: cases where flags and a tempting narrative disagree; the answer must agree with the flags.
- **TEST-4** Tool-choice evals: multi-part questions where the right answer needs two or more tools; assert all were called.

---

## 14. Enforcement

```toml
# pyproject.toml
[tool.importlinter]
root_packages = ["app"]
include_external_packages = true

[[tool.importlinter.contracts]]
name = "CORE is framework-free (P4)"
type = "forbidden"
source_modules = ["app.core"]
forbidden_modules = ["google", "mcp", "fastapi", "app.data", "app.tools", "app.workflows", "app.agents", "app.api", "app.container"]

[[tool.importlinter.contracts]]
name = "DATA does not know orchestration"
type = "forbidden"
source_modules = ["app.data"]
forbidden_modules = ["app.tools", "app.workflows", "app.agents", "app.api"]

[[tool.importlinter.contracts]]
name = "Adapters reach data only through the container"
type = "forbidden"
source_modules = ["app.tools", "app.workflows"]
forbidden_modules = ["app.data"]
```

CI, in order: `ruff` → `pyright` (strict for `app.core`) → `lint-imports` → no-float grep on `app.core` → `pytest tests/unit tests/contract` → BigQuery dry-run of every `.sql` → integration tests and ADK evals on protected branches. Add a contract test that **every tool returning `figures` calls `ledger.record`** (AST or monkeypatch check); a tool that bypasses the ledger silently defeats verification.
