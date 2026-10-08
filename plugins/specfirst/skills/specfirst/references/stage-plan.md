# Spec-first guide — §3.3 PLAN

One stage of the workflow: its purpose, template, rules and a worked example. Rules for the assistant, hard stops, artifacts and naming: [overview.md](overview.md); the stage index is at its end. Templates: [../templates/](../templates/).

---

### 3.3 PLAN

**Purpose.** Map the spec onto the architecture. This is where the assistant is most useful as a designer and where the architecture guide is enforced.

**Who.** Assistant drafts; human reviews for layer placement and scope creep.

**Template.**

```markdown
# P-2609111020-order-export Plan for S-2609111020-order-export v1
Derived from: docs/specs/S-2609111020-order-export.md v1

## Touched layers (architecture guide §3)
domain     new: OrderExportRow and its formatting (DOM-2 exact amounts, DOM-5 no locale); row limit rule
services   new: ExportOrders use case (SVC-1); reuses the orders screen's OrderFilter
storage    extend: OrderRepository.list_filtered takes a row cap (STO-3: no query built from input)
api        new: GET /orders/export (API-2 no formatting in endpoints, API-3 permission before fetch)
ui         orders screen: Export button passing the active filters (UI-2)
tests/e2e  filter, export, compare with the screen (AC-2)

## Decisions
D1  The export reuses the screen's query rather than a second one, so AC-2 holds by construction.
D2  Rows are written with the standard library's CSV writer, not by joining strings (AC-4).

## New dependencies
None.

## Rule exceptions
None. (Any exception → ADR before tasks.)

## External repositories
None.

## Risks
R1  The screen's query may page inside the storage layer → blocks AC-1; verify first (task 1).
R2  Spreadsheets guess the encoding → AC-7 may need a byte-order mark; decide after the manual check.

## Deferred
Other file formats; scheduled exports.
```

**Rules.**

- **PLAN-1** Every new module is placed in a named layer with the rule IDs it must satisfy.
- **PLAN-2** Any rule exception is an ADR, drafted by the assistant as `proposed` and accepted by a person before tasks are cut. The assistant never accepts its own ADR (G1).
- **PLAN-3** The plan lists what it deliberately does not do. "Deferred" is where scope creep goes to die.
- **PLAN-4** Unknowns become the first tasks (spikes), time-boxed, producing a note rather than code.
- **PLAN-5** The plan lists new dependencies explicitly, each with its reason and a note on how it ships (desktop bundle, container image, licence), `None.` when there are none. A dependency that appears later is G3.
- **PLAN-6** The plan lists every other repository the change touches under `External repositories` (repository, branch, what changes there, how it comes back: release and vendor, submodule, pin), `None.` when there is none. A machine path is not a repository name. A change there is one task, `Tier: judgement` (TASK-8), and the run may park on it with a `waits on:` checkpoint (TASK-6).

**Gate → TASKS (self-check).** No person is needed. The assistant proceeds when `Rule exceptions` and `New dependencies` both read `None.` and every touched layer carries rule IDs (PLAN-1). Otherwise G1 or G3 fires: draft the ADR as proposed, or list the dependency, and stop. Layer placement itself is determined by the architecture rules and is checked again at review.

