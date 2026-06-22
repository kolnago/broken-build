# Spec-Driven ADK Development — A Methodology for the Directing Developer

> For an experienced developer who **directs AI to write the code** rather than
> typing it. The specs are the source of truth you author (in prose, converted to
> structure); the working ADK solution is the output. Your job is to **describe
> intent and exercise judgment**, not to write implementation code.

---

## Core philosophy

**You design and decide; AI structures and builds; deterministic checks gate.**

Three actors, three jobs, kept separate:

| Actor | Job | Nature |
|---|---|---|
| You | Describe intent, make architecture & risk decisions, review | Judgment |
| Claude Code | Convert prose → specs, implement specs → code | Generation |
| Skills/hooks | Validate completeness, detect drift, run tests | Mechanical |

The discipline throughout: **put every mechanical job in an automated seat, and
keep every judgment call in your seat.** Drift *detection* is mechanical; deciding
whether the code or the spec is right is yours. Completeness is mechanical; whether
the acceptance criteria are *good* is yours.

---

## The pipeline (prose in, working solution out)

```
   your prose
       │  ┌──────────────────────────────────────────────┐
       ▼  ▼                                               │
  [prose_to_spec]  ── asks you about unstated decisions ──┘   (AI + judgment)
       │            (failure modes, edge cases, scope)
       ▼
  structured spec  (Markdown prose + schema-validated frontmatter & acceptance)
       │
       ▼
  [validate_specs] ── completeness gate, fails fast on gaps   (deterministic skill)
       │
       ▼
  you review the acceptance table  ── the one human check that matters
       │
       ▼
  [BUILD.md reconciliation loop] ── additive, drift-aware     (AI, gated by tests)
       │
       ▼
  acceptance tests prove conformance  ── green = done
```

Each step is the right actor doing the right job. You only ever touch plain
language and review decisions.

---

## The two ADK-specific risks this methodology exists to manage

Everything below is standard spec-first discipline **except** two things that are
unique to building ADK with AI. Name them so the methodology addresses them head-on:

1. **Version drift.** ADK moves fast; AI training data lags it. Left unmanaged, the
   AI writes confident code against renamed/deprecated APIs. *Mitigation:* an
   **ADK-version skill** that reviews the live ADK docs/code for a given version and
   generates current API instructions to follow. This is active regeneration, not
   frozen snippets — the grounding tracks the framework instead of lagging it.
   **You trigger the refresh** when you decide it's time to move to a new ADK version.
2. **The state contract.** Multi-agent systems integrate through shared **State**, a
   surface that doesn't exist in traditional service code. Undocumented, agents
   silently fail to coordinate. *Mitigation:* an explicit state-contract document —
   every key, its scope, who writes, who reads.

If you internalize nothing else: **ground the AI in the real API, and document the
state contract.** Those are the failures that look like "well-structured code that
doesn't work."

---

## Managing version freshness (the active-regeneration model)

Version drift is handled by an **ADK-version skill** rather than frozen reference
code. The distinction matters: frozen snippets are one more thing that goes stale;
a skill *re-derives* current truth on demand.

**How it works:**

1. The skill reviews the live ADK documentation and/or code for a target version and
   **generates instructions** — current API rules, what changed, what's deprecated,
   the correct way to define tools/agents/services at that version. Instructions, not
   just examples, because rules generalize beyond the one case an example covers.
2. The output lands in `07-adk-version/instructions.md` and is the grounding the
   build loop follows. `07-adk-version/derived-from.md` records which ADK version
   the instructions came from.
3. **You trigger the refresh.** Moving to a new ADK version is a deliberate decision
   (the churn is worth it, or it isn't) — not an automatic background process. When
   you decide it's time, you bump `00-foundation/adk-version.md` and re-run the
   version skill.

**The version-match check (closes the quiet failure mode):** the build's validation
step compares `07-adk-version/derived-from.md` against the pinned version in
`00-foundation/adk-version.md`. If they diverge — pinned version moved but
instructions weren't regenerated — the build **stops and tells you to re-run the
version skill** before building. This is the same version-marker discipline used
for spec↔code drift, applied to instructions↔framework. Without it, you can silently
end up grounded in yesterday's API again.

This keeps version-freshness a *managed, deliberate* process: drift can't accumulate
because you have a refresh mechanism, and stale grounding can't slip through because
the build checks for it.

---

## Folder structure

`specs/` is a root, sibling to `docs/`. It is the source of truth.

```
specs/
├── BUILD.md                  # entry point: how to reconcile specs → code
├── README.md                 # what this solution is (2 paragraphs)
├── STATUS.md                 # the build ledger: per-unit status + spec version/SHA
│
├── 00-foundation/            # the grounding layer (manages risk #1)
│   ├── adk-version.md        #   pinned google-adk + Python version, uv setup
│   ├── conventions.md        #   naming, module layout, composition rules, libraries
│   ├── quality-gates.md      #   Pyright strict + Ruff + test requirements
│   └── glossary.md           #   domain terms (keeps agent instructions consistent)
│
├── 01-system/                # system contracts (read BEFORE any component)
│   ├── overview.md           #   what it does, agent topology
│   ├── state-contract.md     #   THE state table (manages risk #2)
│   └── data-models.md        #   shared Pydantic models (tool I/O, structured output)
│
├── 02-tools/                 # one file per tool (most reusable unit)
│   ├── _template.md
│   └── <tool>.md
│
├── 03-agents/                # one file per agent
│   ├── _template.md
│   └── <agent>.md
│
├── 04-orchestration/         # how agents connect — YOUR decision, handed down
│   └── orchestration.md
│
├── 05-services/              # session / memory / artifact wiring (dev vs prod)
│   └── services.md
│
├── 06-callbacks/             # cross-cutting: validation, audit, guardrails
│   └── callbacks.md
│
├── 07-adk-version/          # current API grounding (manages risk #1)
│   ├── instructions.md       #   GENERATED by the ADK-version skill: current
│   │                         #   API rules, what changed, what's deprecated
│   └── derived-from.md       #   the ADK version these instructions were derived
│                             #   from — checked against 00-foundation/adk-version.md
│
└── _intent/                  # your original prose, kept as the human-readable source
    └── <unit>.md
```

**The numbering is also the read order and build order.** Foundation + system
contracts are binding context absorbed first; then build bottom-up (tools →
agents → orchestration → services → callbacks).

---

## The spec file: structure without programming

A spec has two kinds of content, treated differently:

- **Prose** (Purpose, Behaviour, Notes) → stays Markdown. Human-first. Never forced
  into data fields, because that nudges you toward code-like terseness.
- **Contract** (frontmatter, signature, return shape, acceptance criteria) →
  structured & schema-validated. Machine-checkable completeness.

You don't hand-author the structure — **prose_to_spec generates it from your
description.** The structure is an output, not something you type.

### Frontmatter (the bookkeeping that powers drift detection)

```yaml
id: tool.get_weather
implements: tools/weather.py::get_weather   # explicit spec ↔ code mapping
spec_version: 1                             # bump on change → drift signal
status: pending                             # pending | implemented | drifted
```

### Acceptance criteria (the heart — plain cases, become tests)

Each row is one test: **given input → when conditions → expect outcome.** A sentence
with structure, not a function. Claude Code generates the actual test code; you
never write `pytest` by hand.

```yaml
acceptance:
  - id: 1
    given:  { city: "Prague" }
    when:   { api: { status: 200, temp: 12.4, condition: "clouds" } }
    expect: { found: true, temp_celsius: 12.4, condition: "clouds" }
  - id: 3
    given:  { city: "Xyzzyville" }
    when:   { api: { status: 404 } }
    expect: { found: false, raises: false }      # not-found is non-catastrophic
  - id: 5
    given:  { city: "Prague" }
    when:   { api: { status: 500 } }
    expect: { raises: true }                      # real failure surfaces
```

**The test you apply to every acceptance table:** *could I have written these rows
without knowing Python?* If yes, the format is holding your line.

### What NOT to put in a spec

Specs describe the **contract** (observable inputs → outputs → what raises), never
the **implementation** (how to parse, retry logic, internal structure). The moment
you write pseudo-code, you've started programming in prose. Turn it into an
input/output row instead.

---

## How drift between spec and code is detected

A three-signal cascade, ordered by trust. Detection is mechanical; the final
"which is right?" call is yours.

1. **Git + SHA-in-ledger** — `STATUS.md` records the spec's git SHA at last build.
   Current SHA ≠ recorded SHA → spec moved since the code was built. *(detection)*
2. **Version markers** — spec carries `spec_version`; generated code carries a
   `# built from: <spec> @ vN` comment. Disagreement → code hasn't caught up.
   Survives outside git history. *(cross-check)*
3. **Acceptance tests** — when a spec changes, its tests change first and go red.
   Red tests are the real proof that implementation must follow. *(conformance)*

**Minimum viable:** start with #1 and #2 (the `implements` mapping + version in
`STATUS.md`). Add acceptance tests on the **catastrophic-path units first** (tools,
anything auditable) before the looser orchestration layer. This is the
catastrophic-vs-non-catastrophic instinct deciding where rigor is worth its cost.

---

## BUILD.md — a convergence procedure, not a generation script

The build is **additive and idempotent**: it reconciles the codebase toward
`specs/`, doing the minimum to get there. Re-running it on a finished solution is a
near-no-op — that's the test of whether it's truly additive.

The reconciliation loop:

1. **Validate first** — run `validate_specs`, and check that the ADK-version
   instructions match the pinned version (`derived-from.md` vs `adk-version.md`).
   Incomplete spec or stale grounding fails fast with a clear message. The AI never
   gets to guess at a half-written spec or build against a stale API.
2. **Read binding context** — foundation (`00`) + system contracts (`01`), every run.
3. **Read the ledger** — `STATUS.md` to learn what already exists.
4. **Per unit:** conforming code exists → skip. Missing → build. Drifted → update
   *just that unit* (the one-file-per-unit design keeps blast radius small).
5. **Test changed units** — run their acceptance tests; quality gates on changed
   code only.
6. **Update the ledger** — status + version + SHA.

**Conservative by default.** Don't delete code without a corresponding spec change
(might be intentional). Don't rewrite working units for style. Flag drift on
catastrophic-path units for *your* review rather than silently overwriting.
"Clean rebuild of unit X" is an explicit mode you invoke deliberately, never the
default.

---

## The skills/agents this methodology uses

| Capability | Type | Job |
|---|---|---|
| `adk_version` | Skill (you trigger) | Reviews live ADK docs/code for a target version → generates current API instructions. Run on a version bump, by your decision |
| `prose_to_spec` | Agent (judgment) | Convert your prose → structured spec; **ask** about unstated decisions, never invent them |
| `validate_specs` | Skill (deterministic) | Completeness gate: required fields, ≥1 acceptance row, mapping present. Fast, CI-able, the hard gate |
| (optional) spec review | Agent (judgment) | Second opinion on whether criteria are *good*, not just *present*. A review, not a gate |
| `BUILD.md` loop | AI, test-gated | Additive reconciliation specs → code |

**The conversion discipline that makes it trustworthy:** `prose_to_spec` converts
what you *said*, and for anything required-but-unstated it **asks you** rather than
guessing. "You described the happy path — what should happen when the city isn't
found?" That clarifying question is the valuable part; it surfaces the decisions
prose lets you skip.

---

## Quality gates (claw back the compile-time safety net)

Configure these up front so generated code passes the mechanical bar before you
review architecture:

- **Pyright (strict)** — your closest thing to a compiler. Type mismatches,
  unexpected `None`, undefined names.
- **Ruff** — fast lint + format; catches dead code, bad imports, common gotchas.
- **Acceptance tests** — per-spec, the conformance proof. "Run all acceptance
  tests" = the conformance state of the whole solution at a glance.

Run order in the build: validate_specs (+ version-match check) → implement → Ruff →
Pyright → acceptance tests. Each gate is mechanical; your review starts only after
they're green.

---

## Your role, concretely

You do exactly four things, all of them judgment, none of them typing code:

1. **Describe** units in prose ("a tool that gets current weather, Celsius,
   not-found instead of erroring").
2. **Decide** the architecture calls the AI shouldn't improvise — orchestration
   pattern, state scoping, where governance/callbacks go, what enters long-term
   memory.
3. **Answer** the clarifying questions prose_to_spec raises (the unstated edge cases
   and failure modes).
4. **Review** the generated acceptance tables and any flagged drift — deciding, when
   spec and code disagree, which one is right.

Everything else — structuring specs, writing code, writing tests, detecting drift,
enforcing completeness — is mechanical or generative and belongs to the tools.

---

## First-build checklist

- [ ] uv project initialized, Python pinned, ADK installed at a pinned version
- [ ] `adk web` debug loop working (you can run what gets built)
- [ ] credentials/config sorted (API key, env vars)
- [ ] `00-foundation/` filled: version, conventions, quality gates
- [ ] ADK-version skill run for the pinned version → `07-adk-version/` populated
- [ ] `01-system/state-contract.md` drafted (even if small)
- [ ] orchestration pattern chosen and written down
- [ ] Pyright strict + Ruff configured
- [ ] `validate_specs` skill in place as the first build step
- [ ] one tool specced end-to-end (prose → spec → code → passing test) as a pipeline test

---

## Why this fits a directing developer

This is recognizably high-ceremony spec-driven discipline — externalized state,
explicit contracts, mechanical enforcement, traceable acceptance criteria — adapted
for two new realities: **AI writes the code**, and **the framework outruns the
training data**. The methodology keeps you in the seat your experience is worth the
most — architecture, risk judgment, and review — and pushes everything mechanical or
generative onto tools that do it faster and more consistently than hand-typing ever
would.

The honest trade: your main ongoing job becomes **drift detection and decision**,
not authoring. When a tool reports "spec and code disagree," you decide which is
right. That's a judgment seat, and it's exactly where a directing developer belongs.