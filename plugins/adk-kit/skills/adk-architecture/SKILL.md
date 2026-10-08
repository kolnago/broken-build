---
name: adk-architecture
description: Architecture rules for Google ADK 2.x agent apps in Python where numbers must be trustworthy - layers (core, data, tools, workflows, agents, api), figures with provenance, the turn ledger, the derive tool, number verification of answers, and the analyst-agent-in-a-shell pattern. Use this whenever the user writes, changes or reviews code in a Google ADK (adk.dev) project - agents, tools, calculators, services, repositories, SQL, prompts, workflows or the API layer - even if they don't mention architecture, asks where a module belongs or which layer may import what, asks how an agent can show numbers without inventing them, or when a plan, spec or review cites rule IDs like P1, CORE-6, TOOL-5 or VER-2. For ADK API mechanics (Workflow graphs, App and Runner, tests) use adk-workflows, adk-app-runtime and adk-testing; for a Python app without ADK use python-architecture.
---

# ADK agent architecture

Compact version of the architecture guide, the adopted guide for ADK projects (`AGENTS.md` names it;
the `specfirst` workflow, in the `specfirst` plugin, cites its rule IDs). Rule IDs are stable: cite them in plans, reviews and
commits. The full text with rationale and reference code is split by section under
[references/](references/); the `§` numbers below are the guide's own and the table at the end
says which file holds which section. Breaking a rule needs an ADR before implementation.

**Verified against** `google-adk` 2.8.0 for the items the guide marks as verified; re-verified on
`google-adk` 2.11.0 for §8.3–8.5 (2026-10-02). Everything marked `# VERIFY` in the references is
unchecked. ADK changes often: check API shapes against the installed package, never memory.

This skill says where code goes and how numbers stay trustworthy. How the ADK API works is in
the sibling skills: `adk-workflows` (graphs, nodes, `RequestInput`), `adk-app-runtime` (`App`,
`Runner`, services, deployment) and `adk-testing` (offline pytest, evals; the how for TEST-1..4).

## Non-negotiables (§1.1)

1. State which layer(s) a change touches and follow that layer's rules.
2. No arithmetic, comparison, aggregation or rounding outside `core/calc/` (or certified SQL, DATA-6).
3. No `google`, `mcp` or `fastapi` imports under `core/`.
4. Money, quantities and rates are `Decimal`, never `float`.
5. SQL in `.sql` files with named parameters, never built from user or model input.
6. Tools returning numbers return **figure views** (TOOL-3) and record them in the turn ledger (TOOL-5).
7. Every user-facing answer with numbers passes number verification (§9). Never bypass the shell.
8. If a request conflicts with the rules, stop and explain instead of implementing it.
9. Verify ADK APIs against the pinned version. `# VERIFY` code is unchecked.
10. Don't override `_run_async_impl()`, append session events directly, or catch broad exceptions
    in nodes and tools (1.x patterns that break ADK 2.0 retries and human-in-the-loop).

## Principles (§2)

- **P1** The LLM decides and explains; it never calculates. Every number shown comes from code.
- **P2** Constrain the output, not the control flow: a verifier checks every number at the exit.
- **P3** Tools return the next comparisons too (flags, deltas, ratios, ranks), or offer `derive`.
- **P4** Framework-free core. **P5** Typed (Pydantic) contracts at every boundary.
- **P6** Data access through repository `Protocol`s. **P7** Code for what must not vary; the LLM
  for judgement ("if you can write the decision tree, write code").
- **P8** Provenance on every figure. **P9** Identity and entitlements never come from the model.
- **P10** Stable, pinned, re-verified APIs.

## Patterns (§3)

- **A (default)**: analyst agent in a deterministic shell: `prepare` (identity, scope, empty
  ledger) → agent with curated tools → `verify_numbers` → deliver / retry once / figures-only
  fallback. For open questions.
- **B**: fixed workflow; code decides what to compute, the LLM only narrates via `{{figure_id}}`
  placeholders (strict mode §9.5). For regulated or repeatable reports and approvals.
- **C**: plain agent, no shell. Demos and low-stakes lookups only.

## Layers (§4, enforced by import-linter §14)

| Layer | Package | Responsibility | May import |
|---|---|---|---|
| Domain core | `core/` | models, ports, calculators, services, guardrails, errors | stdlib, `pydantic` |
| Data | `data/` | repositories, `.sql` files, row models | `core`, `google.cloud.*` |
| Tools | `tools/` | function-tool adapters, `derive`, turn ledger | `core`, `google.adk` |
| Orchestration | `workflows/` | shells, fixed graphs, prompts | `core`, `tools`, `google.adk` |
| Agents | `agents/` | `root_agent` and `app` entry points | `workflows`, `tools`, `container` |
| API | `api/` | HTTP, auth, session setup | `agents`, `container`, `fastapi` |
| Composition root | `config.py`, `container.py` | settings, wiring | everything |

Imports point inward. `tools` and `workflows` never import `data`; the container injects it.

## Rule groups (details in the references)

- **CORE-1..19** (§6, [references/core.md](references/core.md)): frozen Pydantic domain models,
  `Decimal` with explicit currency/unit, explicit `as_of` dates (no implicit today), separate
  row/domain/tool model families, pure calculators with `CALC_VERSION` and `Provenance`, rounding
  only in `core/calc/rounding.py`. A **Figure** (`figure_id`, `label`, `value`, `unit`,
  code-formatted `display`, provenance) is the unit of exchange; flags and categories are figures
  too. `derive` operations are a closed set in `core/calc/derive.py`. Services are
  question-shaped (CORE-17) and enforce entitlements.
- **DATA-1..9** (§7, [references/data.md](references/data.md)): repositories implement ports; one
  query per `.sql` file; named parameters; explicit `as_of` filter; `maximum_bytes_billed`,
  timeout and row cap; repositories retrieve, calculators compute (aggregating SQL is "certified
  SQL"); money columns are NUMERIC; every port has a fake.
- **AGT-1..5, TOOL-1..9** (§8, [references/tools-and-shell.md](references/tools-and-shell.md)):
  curated question-shaped tools plus `derive`, never raw SQL or table tools. The docstring is the
  tool's prompt (TOOL-2). Tools return figure views only (TOOL-3), primitive parameters (TOOL-4),
  `{"status": "error", "message"}` for domain errors (TOOL-6), compact results (TOOL-9). Prompts
  live in `agents/<name>/prompts/*.md`.
- **LED-1..3** (§8.3): the turn ledger holds this turn's figures under a `temp:` state key; only
  tools write it. It resets every turn; conversation history does not.
- **DRV-1..2** (§8.4): `derive(operation, figure_ids)` computes over ledger figures only.
- **SH-1..4** (§8.5): `prepare` fails fast without identity; verifier feedback drives one retry;
  after that, a figures-only fallback. An unverified answer is never delivered.
- **VER-1..4** (§9, [references/verification.md](references/verification.md)): every numeric
  token in the answer matches a ledger figure (exact, rounded, or unit-scaled) or appears in the
  user's message; tokens with digits (dates, IDs) must appear verbatim. Catches invented and
  computed numbers, not wrong qualitative claims (use flags and consistency evals for those).
- **SEC-1..5** (§10), **ERR-1..3** (§11), **CFG-1..3** (§12,
  [references/state-errors-config.md](references/state-errors-config.md)): the API layer writes
  identity and scope into state; tools read them from context, never from arguments or model
  output; services enforce entitlements; send the model only figure views; catch specific
  exceptions only; settings via `pydantic-settings`; `agent.py` exposes `root_agent` and an `App` wrapping it as `app` (CFG-3).
- **TEST-1..4** (§13, [references/testing-enforcement.md](references/testing-enforcement.md)):
  no test asserts on an LLM-produced number; evals check tool choice, cited figures,
  verification pass rate, and flag consistency.

## Checklists (§15)

- **Calculation**: result model (Decimal, frozen, Provenance) → pure function with name and
  version, including next-step comparisons → figure mapping with stable IDs → unit, golden and
  property tests.
- **Tool**: a question-shaped service exists → docstring as prompt, primitive params, `status` →
  figure views, `ledger.record`, mapped domain errors → contract test → eval cases for when it
  is and isn't the right tool.

## Reference files: which to open when

Open only the file for the layer you are touching; the rules above are enough for placement.

| File | Sections | Read it when |
|---|---|---|
| [references/overview.md](references/overview.md) | §0–5 | you need the rationale for the principles or patterns, the full dependency rule, or the project layout tree |
| [references/core.md](references/core.md) | §6 | writing a domain model, port, calculator, figure mapping, derive operation, service or guardrail (has reference code) |
| [references/data.md](references/data.md) | §7 | writing a repository, `.sql` file or row model, or deciding what may be certified SQL |
| [references/tools-and-shell.md](references/tools-and-shell.md) | §8 | writing a tool, the ledger, the derive tool, the Pattern A shell workflow, or exposing tools over MCP (has reference code) |
| [references/verification.md](references/verification.md) | §9 | implementing or debugging number verification, its matching rules, limits, or Pattern B strict mode (has reference code) |
| [references/state-errors-config.md](references/state-errors-config.md) | §10–12 | identity and session state, exception handling, settings and the composition root |
| [references/testing-enforcement.md](references/testing-enforcement.md) | §13–14 | writing tests or evals, or configuring import-linter and CI |
| [references/checklists-antipatterns.md](references/checklists-antipatterns.md) | §15–18 | the full checklists, anti-patterns with their fixes, open decisions (OD-n), change log |
