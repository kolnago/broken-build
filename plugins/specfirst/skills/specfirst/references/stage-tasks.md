# Spec-first guide — §3.4 TASKS (WIP.md)

One stage of the workflow: its purpose, template, rules and a worked example. Rules for the assistant, hard stops, artifacts and naming: [overview.md](overview.md); the stage index is at its end. Templates: [../templates/](../templates/).

---

### 3.4 TASKS (`WIP.md`)

**Purpose.** Turn the plan into units an assistant can complete in one sitting without judgement calls. `WIP.md` is the scoping fence: if it is not in the file, it is not being built.

**Template.**

```markdown
# WIP — S-2609111020-order-export v1 / P-2609111020-order-export
Autonomy: show tasks
Rules: architecture guide §1.1. Only tasks below. Propose anything else as a comment here.
Done means: the project's Done commands from AGENTS.md (lint, typecheck, import rules, tests), specfirst.py check green + task checks.
Budget: 20 subagent runs.
Mode: run-to-completion, one task per fresh subagent on the model its Tier allows. Hard stops G1–G9 (specfirst §1.1) end the run. Per task: checks → commit "T#: …" → tick → log line.
Every commit carries the trailer `Intent: I-2609111020-order-export`.

- [ ] T1 SPIKE (30 min): confirm the orders query can return every matching row without paging. Output: note in P-2609111020-order-export R1. No code.
      Tier: judgement
      Checks: the note is written under R1 and says whether paging applies.
- [ ] T2 domain: OrderExportRow and its CSV formatting — total with two decimals, ISO date, quoting.
      Tier: judgement
      Checks: unit tests incl. comma, quote, line break, diacritics; golden file.
- [ ] T3 domain: row limit rule — more than EXPORT_MAX_ROWS raises TooManyRows.
      Tier: standard
      Checks: unit at the limit and one above it.
⏸ CHECKPOINT — human reviews the file format before adapters.

- [ ] T4 storage: OrderRepository.list_filtered with a row cap; fake.
      Tier: mechanical
      Checks: integration test on the test database; fake returns the fixture.
- [ ] T5 services: ExportOrders — filter, fetch through the repository, limit rule, rows in screen order.
      Tier: standard
      Checks: unit with fakes; same order as the list use case (AC-2).
- [ ] T6 api: GET /orders/export per API-1..6; permission checked before any fetch.
      Tier: standard
      Checks: contract tests (content type, header row, refusal without orders:read, error shape).
⏸ CHECKPOINT — human reviews the endpoint contract before the screen changes.

- [ ] T7 ui: Export button on the orders screen, passing the active filters (UI-2). No other screen edits.
      Tier: mechanical
      Checks: component test: the request carries the filters.
- [ ] T8 tests/e2e: filter, export, compare the rows with the screen (AC-2).
      Tier: mechanical
      Checks: the e2e test runs green in CI.

## Proposals (not authorised)
- (assistant) T6 would be simpler if the endpoint built the CSV itself → rejected, API-2.

## Review

## Log
- T1 done 2026-09-11 tier=judgement model=session checks=note commit=a1b2c3d — the query returns all rows when no page size is given. R1 closed.
```

**Rules.**

- **TASK-1** One task touches one layer where possible; one green commit always. A task spanning the domain layer and an adapter is two tasks. When an inner-layer change cannot be green without its caller (a rule change that breaks the service that calls it), cut one task that spans both rather than two that cannot each pass Done; `check` warns when two ticked tasks share a commit.
- **TASK-2** Every task names its checks, a spike included: its check is the note it must leave. A task without checks is not a task.
- **TASK-3** Tasks are ordered inside-out, by the layers of the architecture guide: domain logic (calculations, rules) → use cases → storage → adapters and endpoints → UI → end-to-end tests; where the project has a model, prompts and evals come last. Tests exist before the adapter that needs them.
- **TASK-4** Where the project has prompts, a prompt edit is its own task with a diff-sized scope. Prompts are code.
- **TASK-5** `WIP.md` is committed. The log at the bottom is the running record; the PR description links to it. Between changes `WIP.md` is idle: no task lines, any `# WIP` header, a note naming the last change. The next change replaces it from `templates/wip.md`.
- **TASK-6** At most two `⏸ CHECKPOINT` lines per spec, placed only where later tasks depend on earlier outputs, or where behaviour changes. More than two and the run stops being a run. A checkpoint that parks the run on something outside this repository (a pull request elsewhere, a release) says so: `waits on: <repo>#<PR>`; `check` then prints it under Next instead of the next task.
- **TASK-8** A task in another repository (the plan's `External repositories`) is one task, `Tier: judgement`, and its log line names the repository before the hash: `commit=<repo> <hash>`. The fence still holds: nothing changes there that the plan did not name.
- **TASK-7** Every task carries a `Tier:` — `mechanical`, `standard` or `judgement` — decided when the tasks are cut so the human sees at the gate which model will do the work. Mechanical: query files, repositories from an existing interface, fakes, fixtures, text and template edits, the evidence table — the task text fully determines the shape. Standard: use cases, adapters, endpoints, contract tests — needs the architecture rules, little judgement. Judgement: calculations and business rules, security-sensitive code, migrations of existing data, spikes — correctness or a design choice. A task without a tier is standard; a calculation or business rule is never below standard. A project's architecture guide may name its own folders per tier.

**Gate → IMPLEMENT.** Per the spec's `Autonomy`, copied into the `WIP.md` header so the log reader sees why there was or was not a pause: with `show tasks`, a person reads the list once and says go; with `run to verify` or `autonomous`, the assistant continues without waiting. From here it runs the list to the end, gated per task (§3.5). Either way the log is the record a person reads afterwards, so every line has the same shape: `T# done <date> tier=<tier> model=<model> checks=<what ran> commit=<hash> — <one clause>`.

