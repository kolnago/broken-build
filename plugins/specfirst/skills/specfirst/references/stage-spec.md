# Spec-first guide — §3.2 SPEC

One stage of the workflow: its purpose, template, rules and a worked example. Rules for the assistant, hard stops, artifacts and naming: [overview.md](overview.md); the stage index is at its end. Templates: [../templates/](../templates/).

---

### 3.2 SPEC

**Purpose.** Describe observable behaviour precisely enough that two engineers would build the same thing and a test could tell them apart. No file names, no classes, no framework calls.

**Who.** Assistant drafts from the intent; human edits until every acceptance criterion is testable.

**Template.**

```markdown
# S-2609111020-order-export Order list export
Derived from: docs/intents/I-2609111020-order-export.md
Status: draft | approved | implemented | superseded
Version: 1
Autonomy: show tasks
Approved by: human

## Read-back
<the intent restated in the AI's own words — what problem this solves, for whom>

Assumptions made:
- <each thing assumed rather than stated in the intent>

## Behaviour
Given the filters active on the orders screen, the export returns a file with a header row
and one row per matching order, in the order the screen lists them. A user who may not see
orders gets no file. When too many orders match, the user is told to narrow the filter.

## Contracts (shared vocabulary)
- `export_orders(filters)` → CSV file, UTF-8, columns `order_number, placed_on, customer_name, status, total, currency`
- `status` is one of `open`, `paid`, `cancelled`
- `EXPORT_MAX_ROWS`: the most rows one export returns
- permission `orders:read`

## Rules that apply
P1, DOM-2, DOM-5, SVC-1, STO-3, API-2, API-3, UI-2, SEC-1.

## Acceptance criteria
AC-1  With no filter, the file has a header row and one row for every order. (integration)
AC-2  With filters, the file has exactly the orders the screen lists for the same filters, in the same order. (integration, e2e)
AC-3  `total` is written with two decimals and a dot, `placed_on` as `YYYY-MM-DD`, whatever the user's locale. (unit)
AC-4  A value containing a comma, a quote or a line break does not shift the columns. (unit)
AC-5  A user without `orders:read` gets a refusal and no file; no order is fetched. (contract)
AC-6  More than `EXPORT_MAX_ROWS` matching orders → a message to narrow the filter, no partial file. (unit)
AC-7  The file opens in the accountant's spreadsheet with the right columns and diacritics. (manual)

## Not in scope
Other file formats, scheduled exports, columns the screen does not show.

## Open questions
- Q1 What is the value of `EXPORT_MAX_ROWS`? (blocks AC-6)

## Change requests
(added during implementation; each needs a version bump when accepted)
```

**The spec interview.** A good spec comes out of many questions, and the human should be able to answer them by choosing rather than typing. Before asking for approval the assistant interviews everything it needs to write testable acceptance criteria: the intent's open questions, edge cases, error behaviour, what is out of scope, which contracts and identifiers to name. Questions come in batches of at most four, each with two to four proposed answers, a recommended one, and `keep it open`; as many batches as the spec needs, deepest questions first. Twelve to twenty questions is normal for a new screen or flow; group the batches by theme — scope, behaviour, failure, quality — so the human can follow where the interview is. Use the tool's question feature when it has one. Confirmed answers are recorded under `Read-back` as `Decisions (confirmed)`, so a reviewer can see what was decided and by whom; only what the human kept open stays in `Open questions`, and a blocking one still makes the spec unapprovable (SPEC-3). The approval itself is the last question: `approved, show tasks` · `approved, run to verify` · `not yet`, with the project's `Autonomy default:` from `AGENTS.md` as the recommended answer when one is set.

**Rules.**

- **SPEC-1** Acceptance criteria are numbered, testable, and tagged with how they are tested: `unit`, `contract`, `integration`, `e2e`, `eval`, `metric`, or `manual` when only a person can judge it (a document's wording, a check on real hardware). Words may follow the tag: `(integration, with fakes)`, `(manual review)`. Prefer a test; `manual` is for what no test can see.
- **SPEC-2** Contracts name operations, fields, statuses and limits by identifier; the spec fixes the vocabulary the code, the tests and the reviewer share.
- **SPEC-3** A spec with an open question that blocks an AC is not approvable. Resolve it or cut the AC.
- **SPEC-4** Specs describe behaviour visible to a user or a test. If a sentence starts with "the code should", delete it.
- **SPEC-5** The human reviews the Read-back against `Raw intent` first. If it is wrong, the spec is rejected there and the acceptance criteria are not reviewed at all — criteria built on a misread problem are worse than no criteria, because they look like agreement.
- **SPEC-6** A spec that changes a value with an external source — a legal limit, a rate, a published threshold — cites the source for each value, and the value lives in versioned configuration, never in code or tests.
- **SPEC-7** The spec is interviewed before it is approved: every question the assistant would otherwise answer with an assumption is asked, as a choice with a recommendation; answers are recorded as confirmed decisions in the spec. An assumption that was never asked is a defect of the spec, not of the human.

**Gate → PLAN.** Human marks `Status: approved` and sets `Autonomy`: `show tasks` (the assistant pauses once more, at the task list) or `run to verify` (it runs plan, tasks, implementation and review without waiting; checkpoints become log milestones; only hard stops interrupt). This is the last judgement gate before code, so it is where the amount of autonomy is chosen. Assistants may not change an approved spec; they file change requests.

**Autonomous run (§3.9).** When the intent's `go` was `go, autonomous`, there is no spec interview and no human approval here. The assistant drafts the spec from `Raw intent` and `Clarifications`, records every decision it would have asked about under `Assumptions made`, and sets `Status: approved`, `Approved by: ai`, `Autonomy: autonomous`. SPEC-7 does not apply; SPEC-5 moves to VERIFY, where the human reads the read-back and the assumptions first.

