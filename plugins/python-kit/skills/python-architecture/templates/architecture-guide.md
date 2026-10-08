# <Project> — Architecture Guide

| | |
|---|---|
| **Version** | 0.1 (draft) |
| **Date** | YYYY-MM-DD |
| **Sibling of** | the `specfirst` workflow (the *how*); this document is the *what* |
| **Applies to** | Python 3.12+, `uv`, Pydantic v2, <database>, <web or agent framework> |
| **Verified against** | <package versions, date>; anything marked `# VERIFY` is unchecked |

---

## 0. What this application is
<three sentences: who it is for, what it does, what it never does>

## 1. How to use this document
Rules carry stable IDs. Cite them in plans, commits and reviews. Breaking one needs a decision
record (§17) accepted by a person before implementation.

### 1.1 Rules for AI coding assistants
1. Before writing code, state which layer(s) the change touches (§3) and follow that layer's rules.
2. No arithmetic, comparison, aggregation or rounding outside `core/calc/` <and `core/rules/`> (or certified SQL, DATA-6).
3. Never import <framework, database driver, HTTP client, SDK> anywhere under `core/`.
4. <Quantity rule: Money is `Decimal` with currency | `Money` in integer minor units>. Never `float`, never a `REAL` column.
5. SQL lives in `.sql` files with named parameters, never assembled from user or model input.
6. <Persistence rule: every write inside one `UnitOfWork` | every numeric tool result recorded as a figure>
7. No implicit "today" in `core/`; dates are parameters, the clock is a port.
8. <Values with an external source come from versioned configuration with a cited source, never literals>
9. Verify library APIs against the pinned version; `# VERIFY` code is unchecked.
10. If a request conflicts with this guide, stop and explain the conflict instead of implementing it.

## 2. Principles
**P1 — <name>.** <one paragraph>
**P2 — Framework-free core.** Domain models, calculators, rules and services depend on nothing but the standard library and Pydantic. Everything external sits behind a `Protocol`.
**P3 — Exact quantities.** <unit and representation>. Formatting happens in one place.
**P4 — Code for what must not vary; the LLM for judgement.** If you can write the decision tree, write code.
**P5 — <project principle>**

## 3. Layers and the dependency rule
| Layer | Package | Responsibility | May import |
|---|---|---|---|
| Domain core | `core/` | models, ports, calculators, <rules>, services, errors | stdlib, `pydantic` |
| Data | `data/` | repositories, <unit of work>, row models, `.sql` files, migrations | `core`, <driver> |
| Adapters | `adapters/` | <external systems> | `core`, their own libraries |
| <UI / API / Agents> | `<web/ | api/ | agents/>` | <routes, templates | tools, prompts> | `core`, <framework> |
| Composition root | `config.py`, `container.py` | settings, wiring | everything |

Imports point inward toward `core`. `data` and `adapters` implement `core.ports`. Callers never import `data` or `adapters`; the composition root injects them. Enforced in CI (§14).

## 4. Project layout
```
src/<pkg>/
├── core/        models/  ports.py  calc/  <rules/>  services/  errors.py
├── data/        rows/  repositories/  sql/<area>/*.sql  migrations/
├── adapters/
├── <web|api|agents>/
├── config.py  container.py
tests/           unit/  contract/  integration/  fakes/  fixtures/
```

## 5. Core layer
- **CORE-1** Domain models are Pydantic v2 with `frozen=True` and `extra="forbid"`.
- **CORE-2** <Quantity type>: never `float`; unit and currency explicit.
- **CORE-3** Dates are explicit parameters; core never calls `date.today()` or `datetime.now()`; services receive a `Clock` port.
- **CORE-4** Three model families stay separate: row models (`data/`), domain models (`core/`), view or request schemas (<ui layer>). Conversion is explicit: `to_domain()` / `from_domain()`.
- **CORE-5** Ports are `typing.Protocol` classes in `core/ports.py`, named by intent, taking and returning domain models.
- **CORE-6** Calculators <and rules> are pure: no I/O, no clock, no randomness, no global state.
- **CORE-7** Rounding happens only in `core/calc/rounding.py`, with an explicit mode.
- **CORE-8** Every calculator result carries `Provenance`: name, `VERSION`, fingerprint of inputs, source of any external value.
- **CORE-9** Each calculator has a `VERSION`; golden tests pin outputs.
- **CORE-10** Calculators return the comparisons a caller needs next (deltas, shares, flags), not only the headline number.
- **CORE-11** A service implements one use case: resolve inputs, fetch through ports, call calculators, persist, record. No arithmetic, no framework types.
- **CORE-12** Domain errors subclass `DomainError` and carry a safe `user_message`. Core never catches unexpected exceptions.
- <project rules from CORE-13>

## 6. Data layer
- **DATA-1** Repositories implement `core.ports`, take and return domain models, and go through row models both ways. Row models are Pydantic, `frozen=True`, `extra="forbid"`, `strict=True`, mirroring a table or query result exactly; field names equal column and parameter names.
- **DATA-2** SQL lives in `data/sql/<area>/<query>.sql`, one statement per file, loaded with `importlib.resources`. No ORM, no query builders.
- **DATA-3** Values are passed only as named parameters.
- **DATA-4** <Quantity columns are `NUMERIC` | `INTEGER` minor units>. A `REAL` column is a CI failure.
- **DATA-5** Migrations are numbered, forward-only `.sql` files applied by a small runner.
- **DATA-6** Repositories retrieve; calculators compute. Aggregating SQL is certified SQL: named, versioned, reviewed like a calculator, golden-tested.
- **DATA-7** Every port has an in-memory fake in `tests/fakes/`.
- **DATA-8** Every query carries an explicit as-of or date filter; <cost caps: bytes billed, timeout, row cap>.
- <project rules from DATA-9: unit of work, append-only triggers, idempotent imports, content-addressed files>

## 7. Adapters
- **ADP-1** One adapter per external system, behind a port, with its own error mapping to domain errors.
- **ADP-2** Adapters are tested on recorded or anonymised responses; the network is never touched in the suite.
- <project rules>

## 8. <UI | API | Agents>
- <layer rules: routes call services only; templates render view models; tools return typed results; prompts live in files>

## 9. Errors and logging
- **ERR-1** Catch only specific, expected exceptions.
- **ERR-2** Domain errors map to a user message at the boundary; infrastructure errors propagate to one handler that logs and shows a generic message.
- **ERR-3** Logs carry record IDs, never names, amounts or account numbers.

## 10. Configuration
- **CFG-1** Settings via `pydantic-settings` in `config.py`. No `os.environ` reads elsewhere.
- **CFG-2** `container.py` builds clock, repositories, adapters, services and the app with cached factories. Tests never use the container, except the one test that proves the composition root.
- **CFG-3** Values with an external source live in versioned configuration with a source reference and a reviewed date. Changing one is a large change with its source (specfirst SPEC-6).

## 11. Testing strategy
| Target | Test type | Proves |
|---|---|---|
| `core/calc` <, `core/rules`> | unit, golden, property (Hypothesis) | numbers correct and stable |
| `core/services` | unit with fakes | orchestration, error mapping, records written |
| `data/` | integration on a temporary database; contract | migrations from zero, `.sql` parameters and columns equal the row model |
| `adapters/` | contract on recorded responses | mapping and error shape |
| <ui/api/agents> | route tests / evals | <pages render | tool choice, verification pass rate> |

- **TEST-1** Numbers in tests come from golden files, configuration or fixtures with provenance, never from the assistant's head.
- **TEST-2** A contract test checks, for every `.sql` file, that its named parameters and result columns equal its row model's fields.
- **TEST-3** No test asserts on a number produced by an LLM.
- **TEST-4** <network disabled in the suite | evals check tool choice and cited figures>

## 12. Enforcement
import-linter contracts (see the `python-architecture` skill, `references/enforcement.md`): core is framework-free; callers reach data and adapters only through the container. CI runs ruff, pyright, lint-imports, <no-float check>, pytest, `specfirst.py check`.

## 13. Anti-patterns
| Anti-pattern | Why harmful | Instead |
|---|---|---|
| `float` for money | rounding drift | <CORE-2> |
| Arithmetic in a service, route or tool | untestable, unversioned numbers | calculators (CORE-6, CORE-9) |
| Class that is both table and domain model | core depends on persistence | separate families (CORE-4, DATA-1) |
| Literal for a value with a legal source | silently wrong next year | configuration with source (CFG-3) |
| Import of `data` from a caller | dependency rule broken | container injection (§3) |

## 14. Decision records
<`docs/adr/ADR-###.md` files | recorded here as §14.1, sequential numbers (specfirst NAME-8)>

## 15. Open decisions
- **OD-1** <question, options, what would decide it>

## 16. Change log
| Version | Date | Change |
|---|---|---|
| 0.1 | YYYY-MM-DD | Initial draft from the `python-architecture` template |
