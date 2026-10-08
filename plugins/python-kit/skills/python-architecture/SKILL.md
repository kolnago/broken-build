---
name: python-architecture
description: The shape of a Python application's architecture guide and the rules every such project shares - layers with imports pointing inward and a framework-free core, exact money and explicit dates, arithmetic only in pure versioned calculators, ports with fakes, SQL in files, one use case per service, testing by layer, mechanical done, stable rule IDs with ADRs before breaking one. Use this when starting a Python app that AI assistants will build, when writing or revising a project's architecture guide or the rules in its AGENTS.md, when asked where a module belongs or what a layer may import, when choosing import-linter contracts, or when a project has no architecture guide yet and asks for layering, money, date, SQL or testing rules. For Google ADK apps the adk-architecture skill is the adopted guide; this one is the template it and others follow.
---

# Python application architecture

A project built with assistants needs one document that says what the code must look like, with
rules the assistant can cite by ID and a person can hold it to. This skill is the shape of that
document and the rules that turned out identical across two very different projects: an ADK
analyst agent (`adk-architecture`) and a local-first invoicing desktop app
(`prijmy-architecture.md`). Everything else is project-specific and belongs in the project's
guide. The template: [templates/architecture-guide.md](templates/architecture-guide.md).
Enforcement config: [references/enforcement.md](references/enforcement.md).

## What the guide is for

- Assistants read `§1.1` before any code and state which layer a change touches. Plans cite
  rule IDs per module; reviews and commits cite them back. IDs never change meaning or number
  once a plan has cited them; a retired rule keeps its number with a note.
- Breaking a rule needs a decision record before implementation, drafted as `proposed` by the
  assistant and accepted by a person (the `specfirst` workflow's G1).
- Mark anything unverified `# VERIFY` and remove the marker with the version it was verified
  against. Assistants check APIs against the installed package, never memory.

## The shape (template sections)

Front matter with version, date, what it applies to and what it was verified against. Then:
`§0` what the application is · `§1` how to use the document, `§1.1` non-negotiables (at most
twelve) · `§2` principles (`P1..`) · `§3` layers and the dependency rule · `§4` project layout ·
one section per layer with its rules (`CORE-n`, `DATA-n`, `ADP-n`, `UI-n`, …) · errors ·
configuration · testing strategy · enforcement · glossary if the UI language differs from the
code · anti-patterns table · decision records · open decisions · change log.

## Rules every project shares

Adopt these into the guide with the project's own IDs; the template pre-fills them. Rewrite the
wording to the project, keep the substance.

1. **Layers, imports inward.** `core/` imports only the standard library and Pydantic. Data and
   adapters implement `core.ports`. Callers (UI, jobs, agents, API) reach data and adapters only
   through the composition root, never by import. Enforced by import-linter, not by memory.
2. **State the layer first.** Every change names the layer(s) it touches before code, and
   follows that layer's rules.
3. **Framework-free core.** Models, ports, calculators, rules, services, errors: no framework
   types, no I/O, no clock, no global state.
4. **Domain models are Pydantic v2, `frozen=True`, `extra="forbid"`.** Row models, domain
   models and view or request schemas are three families; one class never serves two.
   Conversion is explicit (`to_domain()` / `from_domain()`).
5. **Exact quantities.** Money, rates and quantities are `Decimal` with explicit unit and
   currency, or integer minor units when there is one currency. Never `float`, never a `REAL`
   column. Formatting happens in one place.
6. **No implicit today.** `core/` never calls `date.today()` or `datetime.now()`; dates arrive
   as parameters or through a `Clock` port. Functions name the date they take.
7. **Arithmetic only in calculators.** No arithmetic, comparison, aggregation or rounding
   outside `core/calc/` (and `core/rules/` where rules exist), or in certified SQL. Calculators
   are pure, carry a `VERSION`, return a result with `Provenance` (name, version, inputs
   fingerprint, source of any external value) and the comparisons a caller needs next.
   Rounding only in `core/calc/rounding.py` with an explicit mode.
8. **Ports are `Protocol`s** in `core/ports.py`, named by intent, taking and returning domain
   models. Every port has an in-memory fake in `tests/fakes/`.
9. **SQL lives in `.sql` files**, one statement per file, named parameters only, never
   assembled from user or model input, loaded with `importlib.resources`. No ORM. Repositories
   retrieve, calculators compute; aggregating SQL is certified SQL, named, versioned and
   golden-tested like a calculator.
10. **A service is one use case.** Resolve inputs, fetch through ports, call calculators, persist
    through the unit of work or repository, write the audit or ledger record. No arithmetic, no
    framework types.
11. **Errors.** Catch only specific expected exceptions. Domain errors subclass one base and
    carry a safe user message; infrastructure errors propagate to one handler. Logs carry IDs,
    not personal data or amounts.
12. **Configuration** via `pydantic-settings` in `config.py`; no `os.environ` elsewhere.
    `container.py` wires everything with cached factories; tests never use the container except
    the one test that proves the composition root. Values with an external source (legal
    limits, rates) are versioned data with a source, never literals.
13. **Testing by layer**: unit, golden and property tests for calculators; services with fakes;
    data on a temporary database with a contract test that every `.sql` file's parameters and
    columns match its row model; adapters on recorded responses; routes with a test client.
    Numbers in tests come from fixtures or configuration with provenance, never from the
    assistant's head. No test asserts on a number an LLM produced.
14. **Done is mechanical**: `ruff check` and `ruff format --check`, `pyright`, `lint-imports`,
    `pytest`, plus `specfirst.py check` where the workflow is used. Say which ran.
15. **Anti-patterns are a table**: symptom, why harmful, the rule that fixes it. Assistants
    that keep breaking a rule get a sharper rule or a CI check, not a reminder.

## What stays in the project

Everything domain-shaped: which quantities exist and their unit, the aggregate lifecycle,
append-only rules, legal values and their sources, backup, platforms, UI language and design
system, the LLM's role and its number verification, the exact import-linter contracts. Two
adopted guides show the range: the ADK one has figures, a turn ledger and number verification;
the invoicing one has `Money` in haléře, a unit of work and append-only triggers. Neither rule
set belongs in the other.
