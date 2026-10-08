---
name: python-rules
description: The Python engineering rules an AI agent follows when writing or changing code in a repository built on the adk-modules charter - uv, pyproject.toml as the single source of truth, ruff, mypy strict, Pydantic v2 (a shared strict base model, Annotated constraints, discriminated unions, SecretStr, BaseSettings), explicit dependency injection, an exception hierarchy, structlog, structured async, pytest with fakes over mocks, security, dependency justification, Conventional Commits and a definition of done; every rule tagged MUST, SHOULD or MAY, with a profile that says where the module shape overrides a rule (layout, tests beside code, agent.py reading the environment, tool and callback signatures, Pydantic at brick edges, per-brick errors). Use this when a repository's AGENTS.md names adk-modules or python-rules, when writing or reviewing Python in such a repository, when configuring ruff, mypy, pytest, coverage or import-linter for it, when a plan or review asks whether a change meets the definition of done, or when the agent is about to add a dependency, disable a check or widen scope. For where code belongs and what may import what, use the charter skill; where the two meet, the charter wins and the profile here records it.
---

# Python rules for AI agents

These rules are binding for any AI agent writing or modifying Python in this repository. They
exist so that code written by an agent is indistinguishable from code written by a careful
senior engineer: typed, small, testable, and boring. The `charter` skill says where code
belongs and what crosses an edge; this skill says how the Python inside is written. Where the
two meet, the charter wins, and §14 records each such case.

Rules are tagged **MUST** (hard gate: the change is rejected), **SHOULD** (deviate only with a
one-line justification in the commit) or **MAY**. Configuration fragments that implement them
are in [references/config.md](references/config.md).

## 0. Operating protocol

1. **Read before writing.** Before touching a brick, read it and its test. Never guess an
   interface; open the file, and check an ADK API against the installed package.
2. **Smallest change that satisfies the spec.** No drive-by refactors, no "while I'm here"
   cleanups. Separate commits for separate concerns.
3. **Never silently widen scope.** A new dependency, a new module, a new app, a public API
   change or a schema change is a **hard gate**: stop and ask, or record a decision, before
   proceeding.
4. **Run the toolchain before claiming done:** `make check` (ruff, mypy, import-linter,
   pytest with coverage, `check_modules.py`, pip-audit). Paste the final output in the summary.
5. **No TODOs without an owner and a ticket.** `# TODO(tom, #123): ...` is fine. Bare `# TODO`
   is rejected.
6. **Prefer deleting code to adding it.** When a feature goes, its tests, config and docs go in
   the same change.
7. **Do not disable checks to make them pass.** `# type: ignore`, `# noqa`, `--no-verify` and
   `xfail` require a reason comment and are reviewed as a defect.

## 1. Project layout and tooling

- **MUST** use `uv` for everything: `uv add`, `uv run`, `uv lock`, `uv sync`. Never `pip install`
  directly; never edit `uv.lock` by hand.
- **MUST** keep a single `pyproject.toml` as the source of truth for metadata, dependencies and
  tool config (ruff, mypy, pytest, coverage, import-linter, `[tool.adk_modules]`). No `setup.py`,
  `setup.cfg`, `requirements.txt`.
- **MUST** pin the Python version in `pyproject.toml` (`requires-python`) and `.python-version`.
  Target the newest release the deployment platform and `google-adk` support.
- **SHOULD** group dependencies: runtime in `[project.dependencies]`, dev tooling in
  `[dependency-groups.dev]`, optional extras in `[project.optional-dependencies]`.
- **MUST** have a `Makefile` with at minimum `install`, `lint`, `format`, `typecheck`, `test`,
  `check`. The agent calls `check`, not individual tools.
- Layout follows the charter (§14): `modules/`, `apps/`, `spikes/`, `scripts/`; no `src/`.

## 2. Typing

- **MUST** type every function signature: parameters and return type. `-> None` is explicit.
- **MUST** pass `mypy --strict`. No `Any` in a brick's public signature. Where `Any` is
  unavoidable at a boundary (JSON from outside, an ADK tool result), it is converted to a typed
  model within the same function.
- **MUST** use modern syntax: `list[str]`, `dict[str, int]`, `X | None`. Never `List`,
  `Optional`, `Union` from `typing`.
- **MUST** use `typing.Protocol` for abstractions consumed by other bricks (structural typing).
  Concrete classes do not inherit from the Protocol; they satisfy it. Use `abc.ABC` only for
  shared implementation or an explicit registry.
- **MUST** use `typing.Self`, `type X = ...`, `Literal`, `Final`, `TypedDict` (for externally
  shaped dicts only) and `NewType` for ids (`CaseId = NewType("CaseId", str)`).
- **SHOULD** use `@overload` rather than return-type unions when the return type depends on the
  argument.
- **MUST NOT** use `isinstance` on a Protocol unless it is `@runtime_checkable` and the check is
  at a true boundary.

## 3. Data modelling with Pydantic v2

Pydantic models are what bricks exchange (charter B2), so a shared value is a Pydantic model
even in-process; a throwaway tuple inside one function is not.

- **MUST** use the **v2 API only**: `model_validate`, `model_dump`, `model_json_schema`,
  `field_validator`, `model_validator`, `ConfigDict`. Never `.dict()`, `.json()`, `parse_obj`,
  `@validator`, `class Config:`, `__root__`.
- **MUST** derive every model from one shared base, `StrictModel`, with `extra="forbid"` and
  `frozen=True` (config.md). Mutate by `model_copy(update=...)`.
- **MUST** use `Field(description=...)` on every field of a model that becomes an external
  schema (API, LLM tool, config). Descriptions are documentation and prompt text.
- **MUST** use `Annotated[...]` constraints over custom validators when a built-in exists:
  `Annotated[Decimal, Field(gt=0)]`, `StringConstraints(min_length=1)`, `SecretStr`.
- **MUST** use `SecretStr` / `SecretBytes` for anything secret. Never a plain `str` for tokens,
  passwords or keys.
- **MUST** keep validators pure and local: `@field_validator("x")` for one field,
  `@model_validator(mode="after")` for cross-field invariants. No I/O, no logging in validators.
- **MUST** use `Literal[...]` or `enum.StrEnum` for closed sets, never free strings.
- **MUST** use discriminated unions (`Field(discriminator="kind")`) for polymorphic payloads.
- **MUST** use `pydantic_settings.BaseSettings` for configuration: one settings class, loaded
  once in an entry point, passed in (charter B4, B7). Business code never imports it as a
  module global.
- **SHOULD** use `TypeAdapter` for validating non-model shapes (`list[Item]`).
- **MUST NOT** put behaviour that computes in a model (charter: calculators compute). Validation
  and trivial `@computed_field`s only.
- **MUST** version external schemas when they change incompatibly (`CaseV2`), never mutate
  `CaseV1` in place.

## 4. Module boundaries

What may import what is the charter's (M2–M4, B3, B8), enforced by `check_modules.py` and the
import-linter contract in config.md. The rules below are the Python side of the same thing.

- **MUST** inject dependencies through parameters. No service locators, no module-level
  singletons, no `import settings` deep in a call stack.
- **MUST** keep side effects at the edges: calculators are pure, tools fetch and call,
  adapters do I/O. A function that computes does not also log, write or sleep.
- **MUST** keep files small: a file over ~400 lines or a function over ~50 lines is a smell to
  split, not a target to hit.
- **MUST NOT** use `from x import *`, circular imports, or import-time side effects (no
  network, no file reads, no env lookups at import), except in an entry point (§14).
- **MUST** use `__all__` in every public module and `_private` prefixes for everything else.
- **MUST** name files by noun (`order_total.py`, `builder.py`), never by pattern (`utils.py`,
  `helpers.py`, `common.py` are banned).

## 5. Errors, results and control flow

- **MUST** root a module's error types in one base per module (`class ExposureError(Exception)`),
  with specific subclasses. A port's "not found" is such a subclass (charter port recipe).
- **MUST NOT** catch `Exception` except at the outermost boundary (an app, `__main__.py`),
  where it is logged with traceback and converted. Never `except: pass`.
- **MUST** raise from the original: `raise ExposureError(...) from exc`. Never swallow a cause.
- **MUST** fail fast on invalid input: validate at the boundary, then trust types inside.
- **MUST** refuse input that has no answer with `ValueError` in a calculator, and turn it into
  `{"status": "error", ...}` in the tool that calls it (charter B2); never return a guess.
- **MUST NOT** return `None` to mean error, `-1` to mean missing, or `""` to mean unset. `None`
  means only "legitimately absent".
- **MUST** use `match` for exhaustive handling of enums and unions, with `assert_never` in the
  default arm so mypy catches new variants.

## 6. Naming, style and documentation

- **MUST** follow PEP 8 naming via ruff; **MUST** format with `ruff format`; never argue with
  the formatter.
- **MUST** write Google-style docstrings for every public module, class and function. A brick's
  `__init__.py` docstring follows the charter's form (kind, trust, in, out). A tool's docstring
  is written for the model (charter tool recipe).
- **MUST NOT** write comments that restate the code. Comments explain *why*: a constraint, a
  workaround, a non-obvious decision, with a link.
- **MUST** use f-strings; `%` and `.format` only for lazy logging arguments.
- **MUST** use keyword-only arguments (`*,`) for functions with more than two parameters or any
  boolean parameter, except where ADK fixes the signature (§14).
- **MUST NOT** use mutable default arguments.
- **MUST** use `Decimal` for money and quantities, `datetime` with `tzinfo=UTC`, `pathlib.Path`,
  `enum` over string constants.
- **MUST NOT** use `print` outside `__main__.py`. Use logging.

## 7. Logging and observability

- **MUST** use `structlog`, configured once in the entry point. Bricks obtain a logger via
  `structlog.get_logger()` and never configure handlers.
- **MUST** log structured key-value fields: `log.info("case_opened", case_id=case.id)`.
- **MUST NOT** log secrets, personal data, amounts, full request bodies or prompts containing
  customer data. IDs only.
- **SHOULD** bind a correlation id at the boundary and propagate it with `contextvars`.
- **MUST** use levels honestly: `debug` for developers, `info` for business events, `warning`
  for recoverable anomalies, `error` with `exc_info=True` for failed operations.

## 8. Async and concurrency

- **MUST** keep a brick sync or async, not both; an async function never calls blocking I/O
  (`asyncio.to_thread` for the unavoidable case). ADK agents and their tests are async.
- **MUST** use `asyncio.TaskGroup` over bare `create_task` / `gather`.
- **MUST** set timeouts on every external call. No unbounded waits.
- **MUST** make retries explicit and bounded (`tenacity`), with jitter, only for idempotent
  operations.
- **MUST NOT** share mutable state across tasks without a lock or a queue. A brick's module
  holds no mutable state (charter agent recipe).

## 9. Testing

- **MUST** use `pytest`, `pytest-asyncio` in `asyncio_mode = "auto"`. No `unittest.TestCase`.
- **MUST** keep each brick's test beside it as `test_<name>.py` (charter B5), running offline.
- **MUST** write a test for every bug fix that fails before the fix and passes after.
- **MUST** test behaviour through the brick's package; never a private function directly, never
  log messages or call counts unless that *is* the behaviour.
- **MUST** use fakes that satisfy the Protocol and the scripted model over `MagicMock`. Mock
  only at a true I/O boundary.
- **MUST** keep tests pure: no network, no filesystem outside `tmp_path`, no sleep, no real
  clock (the clock is a parameter, charter B4).
- **MUST** name tests as sentences: `test_rejects_mixed_currencies`, not `test_1`.
- **MUST** use `pytest.raises(SpecificError, match=...)`, never `pytest.raises(Exception)`.
- **MUST** treat warnings as errors (`filterwarnings = ["error"]`).
- **MUST** keep branch coverage ≥ 85% on `modules/`; a new brick ships at 100% or with a
  justified exclusion.
- **SHOULD** use `hypothesis` for calculators, parsers and anything with an inverse.
- **MUST NOT** assert on a number a real model produced. Evals measure prompts; tests prove code.

## 10. Security and secrets

- **MUST** load secrets through `BaseSettings` in an entry point; never from committed files.
  `.env` is gitignored and in `.dockerignore`; `.env.example` has placeholders only.
- **MUST** pass ruff's `S` (bandit) rules; `S101` is allowed only in tests.
- **MUST NOT** use `eval`, `exec`, `pickle` on untrusted data, `yaml.load` without `SafeLoader`,
  `subprocess` with `shell=True`, or string-built SQL.
- **MUST** validate and bound everything from outside: size limits, allow-lists, `extra="forbid"`.
- **MUST** run `pip-audit` in `make check`; a known-vulnerable dependency blocks merge.
- **MUST** treat model output as untrusted input: parse it into a `StrictModel` before acting
  on it; never execute or template it raw. A strict brick never repeats a free brick's number
  (charter, Trust).

## 11. Dependencies

- **MUST** justify every new runtime dependency in the commit: what it does, why the stdlib or
  `google-adk` is insufficient, maintenance status, license. This is a hard gate.
- **MUST** pin via `uv.lock`; `pyproject.toml` uses compatible ranges (`>=2.7,<3`).
- **SHOULD** prefer `httpx`, `structlog`, `typer`, `pydantic-settings`, `tenacity`,
  `sqlalchemy 2.x` with typed `Mapped[]`, `polars` over `pandas` for new tabular code.
- **MUST NOT** vendor code or paste from the internet without attribution and a license check.

## 12. Git and change hygiene

- **MUST** write Conventional Commits with the module as scope: `feat(exposure): add pdlc
  netting`. The body explains *why* and names the rule IDs a reviewer should check.
- **MUST** keep one logical change per commit; formatting and logic are split.
- **MUST** install pre-commit hooks (`ruff`, `ruff-format`, `mypy`, `lint-imports`,
  `check_modules.py`) and never bypass them.
- **MUST** record a decision when a rule of the charter or of this skill is bent or a module is
  added, in the form the project's workflow uses (an ADR under `docs/decisions/`, or the
  `specfirst` intent when that plugin is installed). The decision is a person's (charter P6).
- **SHOULD** keep a `CHANGELOG.md` (Keep a Changelog) for every user-visible change.

## 13. Definition of done

A change is complete only when all of the following are true:

- [ ] `make check` passes: ruff lint and format, mypy strict, import-linter, `check_modules.py`,
      pytest with coverage ≥ threshold, pip-audit.
- [ ] Every new public function and class is typed and documented; every new brick's
      `__init__.py` states kind, trust, in and out.
- [ ] Every new boundary model derives from `StrictModel` with field descriptions.
- [ ] Every behaviour change has a test beside the brick; every bug fix has a regression test.
- [ ] No new `# type: ignore`, `# noqa`, `xfail` or `TODO` without owner and reason.
- [ ] No new dependency, module or public API without a recorded decision.
- [ ] Commits follow Conventional Commits and explain *why*.
- [ ] The summary lists files changed, tests added, commands run with output, and any deviation
      from these rules with its justification.

## 14. Profile: where the module shape overrides a rule

The charter was proven on ADK before these rules were written for it; where ADK or the brick
shape forces a different answer, the charter wins and this table records it, so a reviewer
does not flag the exemption as a defect.

| Rule here | Charter | Exemption |
|---|---|---|
| §1 `src/` layout, import-linter `layers` on domain/application/adapters | M3, M4, repository shape | layout is `modules/`, `apps/`, `spikes/`; import-linter enforces the *module order* and the *kind order* (config.md) |
| §9 tests mirror the tree under `tests/` | B5 | `test_<name>.py` beside each brick; `testpaths = ["modules", "apps"]` |
| §4 no env lookup at import; §3 one `BaseSettings` passed in | B7 | `agent.py` and `__main__.py` are entry points: they may read the environment (or build the settings) at import, because `adk web` needs a module-level `root_agent`; nothing else may |
| §6 keyword-only arguments | tool and callback recipes | a tool function's parameters are positional primitives (ADK builds the schema from them); a callback's parameters are ADK's exact names; `build_<name>(model, ports...)` SHOULD use `*,` after `model` |
| §3 Pydantic at boundaries only | B2 | every value bricks exchange is a Pydantic model, in-process or not |
| §5 one exception hierarchy per project | port recipe, M2 | one base per module; a tool converts any domain error to `{"status": "error"}` because ADK tools return dicts |
| §2 no `Any` in public signatures | tool recipe | a tool returns `dict[str, object]`; `Callable[..., dict[str, object]]` for the factory. `mypy --strict` on ADK's own callback and agent types is not yet proven on a sample; where ADK forces a `type: ignore`, the reason names the ADK version |
| §12 ADRs | P4, P6 | the decision is recorded in whatever the project's workflow uses; `specfirst` when installed |
