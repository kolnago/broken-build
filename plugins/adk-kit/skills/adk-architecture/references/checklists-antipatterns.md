# ADK architecture guide v2.0 — §15–18 Checklists, anti-patterns, open decisions, change log

Part of the guide split by section. Rule summary and file index: [../SKILL.md](../SKILL.md); overview, principles and layers: [overview.md](overview.md).

---

## 15. Checklists

**Adding a calculation**
1. Result model in `core/` with `Decimal`, frozen, `Provenance`.
2. Pure function in `core/calc/` with `CALC_NAME` and `CALC_VERSION`; include the next-step comparisons (P3).
3. Figure mapping with stable `figure_id`s and code-formatted `display`.
4. Unit, golden, property tests.

**Adding a tool**
1. Confirm a question-shaped service exists; the tool only adapts it.
2. Docstring as prompt (`TOOL-2`); primitive parameters; `status` in the result.
3. Return figure views only; call `ledger.record`; map domain errors.
4. Contract test: schema snapshot, ledger written, JSON safe.
5. Add an eval case where this tool is the right choice and one where it is not.

**Adding a derive operation**
1. Implement in `core/calc/derive.py` with unit checks and provenance.
2. Add to `OPERATIONS` and the `Literal` in `tools/derive.py`.
3. Unit tests including mismatch and zero cases.

**Adding a Pattern B workflow**
1. Justify in an ADR why the control flow must be fixed.
2. Follow §9.5 strict mode for narration.
3. Node unit tests and an eval set.

---

## 16. Anti-patterns

| Anti-pattern | Why harmful | Instead |
|---|---|---|
| LLM sums, compares, or computes percentages in prose | Silent, plausible, wrong numbers | Precomputed figures; `derive` tool; verification |
| Tools returning raw rows or bare floats | Verifier cannot ground them; model tempted to aggregate | Figure views (`TOOL-3`) |
| Tool that returns figures but skips the ledger | Verification silently defeated | `ledger.record` in every figure-returning tool |
| Fixed graph for open-ended questions | Model reduced to narration; no value from the LLM | Pattern A shell |
| Free agent with no shell in production | Invented numbers reach users | Pattern A shell |
| Delivering an answer that failed verification | Defeats P1 | Retry, then figures-only fallback |
| `float` for money or rates | Rounding drift | `Decimal` |
| SQL built with f-strings | Injection, unreviewable | `.sql` files + named parameters |
| Generic `execute_sql` tool in production | Model writes the business logic | Curated services and tools |
| ADK or GCP imports in `core/` | Untestable, lock-in | Ports and adapters |
| `datetime.now()` in calculations | Non-reproducible | Explicit `as_of` |
| Identity from tool arguments | Privilege escalation via prompt | Context set by API layer |
| Broad `except Exception` in nodes | Breaks ADK retries and HITL | Specific exceptions |
| Overriding `_run_async_impl()` or appending session events | 1.x patterns that break in 2.0 | Workflow nodes and `Event` |
| `"END"` as a graph target / message-only routed events | `Workflow(...)` fails validation; the successor gets `node_input=None` | Terminal nodes; routed events carry `output` |

---

## 17. Open decisions

| ID | Decision | Notes |
|---|---|---|
| OD-1 | Rounding and display policy per unit | Central in `core/calc/rounding.py`, `formatting.py` |
| OD-2 | Matcher extensions: scale words, currency symbols, negative-as-parentheses | Default is strict (§9.2) |
| OD-3 | Certified SQL vs Python aggregation boundary per dataset | Performance vs reviewability |
| OD-4 | Production session service and state persistence | Cost and latency |
| OD-5 | Model per role (analyst, Pattern B intake/narration) | Verify tool-calling and structured-output support |
| OD-6 | Verification placement: graph node (default) vs `after_model_callback` | See `SH-4` |
| OD-7 | Query identity: service account vs end-user delegation | Row-level security implications |
| OD-8 | Trigger and topology for MCP exposure | See §8.6 |
| OD-9 | Streaming: verification requires the full answer; decide whether to buffer or verify per paragraph | UX vs guarantee |

---

## 18. Change log

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-10 | Initial draft: fixed graph, placeholder-only narration |
| 2.0 | 2026-09-10 | Analyst agent in a shell as default; number verification and turn ledger replace the digit ban; `derive` tool; fixed graphs and strict mode reserved for regulated processes; consistency evals |
