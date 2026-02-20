# Working Effectively with Claude — Pactum Project

A practical workflow for AI-assisted development on the Pactum legal agreement system.
Covers session management, living documentation, feature specs, and change requests.

---

## The Core Problem

Claude has a finite context window. In long sessions, earlier content gets compressed or dropped,
and Claude starts losing track of decisions, constraints, and progress. The solution is to
**manage context deliberately** across short, focused sessions backed by persistent documents.

**The document is the memory, not the conversation.**

---

## Document Structure

```
/docs
  LIVING.md                          ← master context file, read at session start
  templates/
    ADR-TEMPLATE.md                  ← architecture decision record template
    SPEC-TEMPLATE.md                 ← feature spec template
    CR-TEMPLATE.md                   ← change request template
  architecture/
    ADR-001-modular-monolith.md
    ADR-002-no-repository-pattern.md
    ADR-003-oracle-schema-no-changes.md
    ADR-004-module-boundary-rules.md
  specs/
    agreements/
      SPEC-001-agreement-domain.md
      SPEC-001-CR-001-description.md
    counterparties/
      SPEC-002-counterparty-domain.md
  CHANGELOG.md                       ← running log of what changed and when

/wip
  current-task.md                    ← temporary, deleted when task is done
```

---

## The Two Document Types

### 1. Living Document (`LIVING.md`)

The master context file. Read by Claude at the start of every session.
Contains current state of the system — architecture decisions, module status,
established patterns, and recent changes. **Updated at the end of every session.**

Never gets too large — resolved details are summarized to one line and archived to
their respective ADR/SPEC files. Only active, Claude-relevant information stays here.

### 2. WIP Document (`/wip/current-task.md`)

Temporary working document for the current task or feature.
Created at task start, deleted when done.
Contains user story, analysis, action plan, and progress log for one focused piece of work.

---

## LIVING.md Structure

```markdown
# Pactum — Living Architecture Document
Last updated: [date] — [what changed]

## What This System Is
Legal agreement management system. Manages agreements, versions, contract parts,
counterparties, netting groups, and dictionaries. Corporate users via Entra ID.
Migrating from legacy .NET 4.6 / Angular / 7-tier architecture.

## Technology Stack
- .NET 8, C#, Blazor Interactive Server
- MudBlazor for UI components
- Oracle database — existing schema, column names preserved
- EF Core direct in handlers — no repository pattern
- MediatR CQRS — Command + Handler in one file per feature
- Entra ID authentication via Microsoft.Identity.Web
- FluentValidation for command validation
- xUnit, NetArchTest, Playwright for testing

## Architecture Decisions Summary
| ADR | Decision | Rationale |
|---|---|---|
| ADR-001 | Modular monolith, 4 projects | No microservice overhead |
| ADR-002 | No repository pattern | EF is already repo+UoW |
| ADR-003 | Oracle schema unchanged | Migration risk, existing data |
| ADR-004 | Module-scoped DbContexts | Compiler-enforced boundaries |

## Module Status
| Module | DB Prefix | DbContext | Spec | Status |
|---|---|---|---|---|
| Agreements | A_ | AgreementsDbContext | SPEC-001 | In Progress |
| Dictionaries | BD_ | DictionariesDbContext | — | Not Started |
| Counterparties | CP_ | CounterpartiesDbContext | — | Not Started |
| Netting | N_ | NettingDbContext | — | Not Started |
| Reports | — | (read-only, multiple) | — | Not Started |

## Patterns Claude Must Always Follow

**Domain layer:**
- Private setters on all properties
- Private parameterless constructor for EF
- Factory methods (`Create`, `CreateCopyOf`) not public constructors
- `internal static` on child entity factories — aggregate root controls children
- Cross-module references are typed IDs only (`CounterpartyId`), never navigation properties
- `DomainException` for business rule violations
- No EF references anywhere in Domain project

**Application layer:**
- Command + Handler always in one file
- Validators check structural validity only (empty fields, format) — business rules live in domain
- `NotFoundException` for missing aggregates
- Handlers: load aggregate → call domain method → save → map to DTO
- No business logic in handlers

**Infrastructure layer:**
- All EF mapping in `IEntityTypeConfiguration` classes
- Oracle column names in configurations, never in domain
- `HasField("_fieldName")` to access private backing fields
- Read models (keyless entities) for cross-module display queries

**Testing:**
- Domain tests: pure C#, no mocks, no infrastructure
- Application tests: EF + SQLite in-memory or Testcontainers Oracle
- Never mock DbContext — use real EF in integration tests
- NSubstitute only for non-database dependencies (ICurrentUserService etc.)
- New tests for CRs go in separate class suffixed `_CR001`

## Current Domain Objects
[Paste latest version of key domain files here — Claude uses these as ground truth]

## Recent Changes (last 5)
[Most recent first]
- [date] SPEC-001: Agreement domain implemented
- [date] ADR-001 through ADR-004 recorded

## Open Questions
[Unresolved items needing stakeholder or architectural input]
- Q: Can a contract part be assigned to versions across different agreements?
- Q: What happens to a draft version when agreement is terminated?
```

---

## Spec and Change Request Framework

### Why This Exists

Business rules discovered late, requirements that change, stakeholder corrections —
these are inevitable. Without a framework, changes get applied informally, Claude loses
track of what was decided, and six months later nobody knows why the code does what it does.

**Immutability principle: never edit past decisions. Always append.**

---

### Feature Spec (`SPEC-NNN.md`)

Written before implementation. Stakeholders review Business Rules section only.
Claude uses the full document to implement the vertical slice.

```markdown
# SPEC-001: Agreement Domain
Module: Agreements
Date: [date]
Status: Approved
Implemented: [date]

## Context
[What this feature is, who uses it, why it exists]

## Entities Involved
- Agreement — master contract record
- AgreementVersion — versioned snapshot of terms
- ContractPart — independent reusable clause, assigned to versions

## Business Rules
[Stakeholders review and sign off on this section only]

1. Agreement must have a name to be created
2. A new version can only be created from an Approved version
3. Only one Draft version may exist per agreement at a time
4. A version must have at least one contract part before approval
5. Contract parts can only be assigned to Draft versions
6. Creating a new version copies all contract part assignments from source
7. When a new version is created, source version becomes Superseded
8. A terminated agreement cannot have new versions created

## State Transitions
Agreement:   Draft → Active → Terminated
Version:     Draft → Approved → Superseded
ContractPart: Active → Inactive

## Actions This Feature Implements
- Create agreement
- Create initial version
- Create new version from approved version
- Assign contract part to draft version
- Remove contract part from draft version
- Approve version
- Activate agreement
- Terminate agreement

## Out of Scope
- Counterparty assignment (separate spec)
- Notifications (handled by event listeners)
- Document generation

## Oracle Tables
[Paste actual table DDL or column list]

## Open Questions
[Unresolved at time of writing]

## Architecture Context
[Paste standard context block — same in every spec]
Pattern: Clean Architecture Modular Monolith
CQRS with MediatR, Command + Handler in one file
No repository, direct DbContext in handlers
Domain: rich entities, private setters, factory methods
EF mapping: Infrastructure only
Module DbContext: AgreementsDbContext
Cross-module refs: IDs only
Tests: Domain unit (pure C#), Application integration (EF + SQLite)
```

---

### Change Request (`SPEC-NNN-CR-NNN.md`)

Raised when a business rule changes or something was missed.
Never modifies the original spec — appends a new file.

```markdown
# SPEC-001-CR-001: [Short Description]
Against: SPEC-001-agreement-domain.md
Date: [date]
Requested by: [name]
Approved by: [name]
Status: Approved / Implemented

## Original Rule (SPEC-001, Rule N)
> [Paste the exact original rule being changed]

## What Changed and Why
[Business context — why this rule is wrong or incomplete]

## New Rules
Na. [New rule replacing or extending original]
Nb. [Additional rule if needed]

## Impact
- Domain: [which file, which method]
- Application: [which handlers affected]
- Tests: [what changes, what new tests needed]
- DB: [any schema impact — usually none]

## What Does NOT Change
- [Explicitly list things that stay the same]
- [Existing tests that must continue passing]

## Open Questions Resolved
- Q: [question from original spec]
- A: [answer this CR provides]

## Claude Implementation Prompt
[Ready-to-use prompt for implementation session]

Read in order:
1. docs/LIVING.md — current system state
2. docs/specs/agreements/SPEC-001-agreement-domain.md — original spec
3. This CR document — the change to implement
4. [paste relevant current domain files]

Implement SPEC-001-CR-001:
- Only modify files listed in Impact section
- Do not modify existing passing tests
- Add new tests in separate class AgreementTests_CR001
- If anything is unclear, ask before generating code
```

---

### Architecture Decision Record (`ADR-NNN.md`)

For architectural decisions that affect the whole system or a module.
Written once, never edited. Superseded by a new ADR if decision changes.

```markdown
# ADR-002: No Repository Pattern
Date: [date]
Status: Accepted
Deciders: [names]
Supersedes: —
Superseded by: —

## Decision
EF Core DbContext injected directly into MediatR handlers.
No IRepository interfaces or Repository implementations.

## Context
[Why this decision was needed]

## Consequences
[What this means going forward — positive and negative]

## Alternatives Considered
[What was rejected and why]
```

---

### Numbering Convention

```
ADR-001, ADR-002...              architecture decisions (system-wide)
SPEC-001, SPEC-002...            feature specs (one per module/feature)
SPEC-001-CR-001, CR-002...       change requests against a specific spec
```

CHANGELOG.md tracks everything in chronological order:

```markdown
# Pactum Changelog

## 2026-03-15
- SPEC-001-CR-001: Version copy now carries inactive parts (approved: [name])

## 2026-02-20
- SPEC-001: Agreement domain implemented
- ADR-001 through ADR-004: Core architecture decisions recorded
```

---

## Session Workflow

### Starting a Session

**Always start with the living document:**

```
Read docs/LIVING.md fully before doing anything.

Confirm you understand:
- The architecture and patterns to follow
- Current module status
- Any open questions

Then read: [paste relevant spec or CR if working on a specific feature]

Current task: [describe what we are doing today]

Relevant existing files:
[paste current domain class / handler / test file]

Ask clarifying questions before generating any code.
```

### During a Session

One task per session. Keep scope tight.

If scope expands mid-session, stop and add the new item to the WIP doc as a future task.
Do not try to solve it in the same session.

### Ending a Session

Before closing, ask Claude:

```
Summarize what we built or decided today.
Update the LIVING.md to reflect:
- Any new patterns established
- Module status changes
- New open questions that came up
- Recent changes log entry

Also list any follow-up tasks for the next session.
```

Paste the updated LIVING.md content back into your file before closing.

---

## WIP Document (per task)

For non-trivial tasks, create `/wip/current-task.md`. Delete when done.

### Phase 1 — User Story
```
Write a user story for: [feature description]
```

### Phase 2 — Analysis
```
Analyze this user story. Identify risks, dependencies, edge cases,
impact on existing domain objects, and EF mapping considerations.
```

### Phase 3 — Action Plan
```
Create a numbered action plan. Each task must be completable in one session.
Flag anything that needs stakeholder clarification before implementation.
```

### Phase 4 — Execute (one session per task)

Paste at session start:
```
Project context: [paste LIVING.md]
WIP doc: [paste wip/current-task.md]
Current task: Task N — [description]
Relevant files: [paste]
```

### Phase 5 — Update WIP After Each Task

```markdown
## Progress

### Task 1 — Done
[What was done, any deviations from plan, decisions made]

### Task 2 — In Progress
...
```

Log deviations explicitly. Next session makes wrong assumptions if it only sees the original plan.

### Phase 6 — Done? Delete the WIP File

It served its purpose. Update LIVING.md and CHANGELOG.md. Then delete.

---

## Key Principles

**Document is the memory, not the conversation.**
Fresh session + good context file beats long session every time.

**Immutability — never edit past decisions, always append.**
Original specs stay unchanged. Changes go in CR files. ADRs get superseded not edited.

**Stakeholders review business rules only.**
The Business Rules section of a spec is written in plain language for non-technical sign-off.
Everything else is for Claude and developers.

**Scope creep kills sessions.**
If something new surfaces mid-session, write it down and handle it next session.

**No informal changes to domain logic.**
Every change to an existing business rule gets a CR — even a small one.
One paragraph minimum. Future you will thank you.

**CLAUDE.md for standing constraints.**
Add a `CLAUDE.md` to project root. Claude Code reads it automatically every session.
Put architecture rules, patterns, and hard constraints there as a backstop.

---

## CLAUDE.md Starter (project root)

```markdown
# Pactum — Claude Standing Instructions

## Architecture
Modular Monolith. Clean Architecture. 4 projects: Domain, Application, Infrastructure, Web.
Always read docs/LIVING.md at session start for current state.

## Non-Negotiables
- No EF references in Domain project — ever
- No repository pattern — DbContext direct in handlers
- Command + Handler in one file
- Private setters on all domain entity properties
- Cross-module references are typed IDs only — no navigation properties
- Business rules in domain methods — not in handlers or validators
- Do not modify existing passing tests — add new ones for changes

## When in Doubt
Ask before generating. One wrong assumption in domain logic
creates a cascade of incorrect tests and handler code.
```

---

## Change Request Decision Tree

```
Something needs to change
         ↓
Is it an architecture pattern?
  Yes → New ADR (supersedes old if conflict)
  No  ↓
Is it a brand new feature?
  Yes → New SPEC
  No  ↓
Is it changing an existing business rule?
  Yes → CR against the relevant SPEC
  No  ↓
Is it a bug (rule was right, code was wrong)?
  Yes → Fix the code, note in CHANGELOG, no CR needed
```
