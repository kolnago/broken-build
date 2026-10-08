# S-<key> <title>
<!-- <key> = the intent's YYMMDDHHMM-slug (NAME-3); never a new timestamp or slug -->
Derived from: docs/intents/I-<key>.md
Status: draft | approved | implemented | superseded
Version: 1
Autonomy: show tasks | run to verify | autonomous   <!-- set by the human at approval; run to verify = only hard stops interrupt until VERIFY; autonomous = chosen at the intent's go, spec approved by the AI (§3.9) -->
Approved by: human | ai   <!-- ai exactly when Autonomy: autonomous (AUTO-1) -->
<!-- project fields go here, as AGENTS.md defines them, e.g. `Design system: <version read>` -->

## Read-back
<the intent restated in your own words: what problem this solves, for whom (SPEC-5)>

Decisions (confirmed in the spec interview, SPEC-7):
- Q# → <answer the human chose>

Assumptions made:
- <each thing assumed rather than stated in the intent and not asked — should be empty; in an autonomous run, every decision taken on the human's behalf (AUTO-2)>

## Behaviour
<Observable behaviour. No file names, no classes, no framework calls (SPEC-4).>

## Contracts (shared vocabulary: identifiers for operations, fields, statuses, limits)
- `<operation or endpoint>(args)` → <what it returns, by name>

## Rules that apply
<rule IDs from the architecture guide, e.g. P1, DOM-2, API-3>

## Acceptance criteria
<!-- Numbered, testable, tagged: unit | contract | integration | e2e | eval | metric | manual (SPEC-1). -->
AC-1  <testable statement>. (unit)

## Values with sources
<!-- Only if the spec changes a value with an external source: value, source, where it lives in configuration (SPEC-6). -->

## Not in scope

## Open questions
- Q1 <question> (blocks AC-#)

## Change requests
(added during implementation; each accepted change needs a version bump)
<!-- autonomous run: REVISED v<n> <date> — <what changed and why> (G4 in §3.9) -->
