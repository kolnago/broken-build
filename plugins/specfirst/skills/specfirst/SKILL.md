---
name: specfirst
description: Spec-first workflow for projects in any language or framework built with AI assistants (INTENT → SPEC → PLAN → TASKS → IMPLEMENT → REVIEW → VERIFY → LEARN) with three human gates, an autonomous mode that runs a large change from intent to verify, hard stops, tiered delegation to cheaper models, keyed artifact naming, templates and a check script. Use this whenever the user wants to add or change behaviour in a project whose AGENTS.md or CLAUDE.md names spec-first or that has docs/intents, docs/specs, docs/plans or a WIP.md - even if they just say "add X" and never mention specs - so the change is triaged small or large before any code. Also use when asked to process an intent, run an intent autonomously ("go, autonomous"), resume after a hard stop, draft a spec or plan, cut tasks into WIP.md, implement from WIP.md, review a change, verify acceptance criteria, write an ADR, record learnings, or set up the docs layout for spec-first work.
---

# Spec-first workflow

Words first, code last. Each stage produces a short artifact the next stage consumes. Three
gates need a person: reviewing the intent, approving the spec, judging the evidence at the end.
The other gates are self-checks that pass unless a hard stop fires. The guide is split under
[references/](references/): [overview.md](references/overview.md) has the rules, hard stops and
naming; one file per stage has that stage's rules and a worked example;
[appendix.md](references/appendix.md) has roles, prompts and anti-patterns. Templates:
[templates/](templates/).

The **architecture guide** below is the project's own, a file or a skill named in its
`AGENTS.md`. A project without one writes a page from
[templates/architecture-guide.md](templates/architecture-guide.md) first. This workflow never
depends on a language or framework: lint, typecheck, import rules and tests are whatever the
project lists as `Done commands:` in `AGENTS.md`.

```
INTENT → SPEC → PLAN → TASKS → IMPLEMENT → REVIEW → VERIFY → LEARN
  human    human    self     autonomy   hard stops  fresh eyes   human
```

## Every change starts as an intent; then small or large? (§2.2)

`docs/intents/` is the log of what was done to the application. The human does not write code.

An intent is a problem a person owns, frozen in their words. A spec is a behaviour a test
owns, written so it can be proven. To place a sentence, ask who would have erred if it turned out
wrong: "that is not what I asked for" belongs to the intent, "that is what I asked for, but it
behaves wrongly" to the spec. Intent questions confirm the request; solution choices wait for the
spec interview.

- **Small**: a fix, tooling tweak, dependency bump, wording change, anything whose correct
  behaviour is obvious or already in an approved spec. Intent → read-back → `go` → do it, run
  Done, one commit, hash into `Closed by:`. One round trip.
- **Large**: new behaviour, anything two people would build differently from the same sentence,
  a change to a value with an external source. Intent → spec → build.
- Not obvious: more than ~3 sentences to explain, or you can't write the test first → large.
- **Large, autonomous** (§3.9, [stage-autonomous.md](references/stage-autonomous.md)): the human
  answers the intent's last question with `go, autonomous`. You write the spec with every
  unasked decision under `Assumptions made`, approve it yourself (`Approved by: ai`,
  `Autonomy: autonomous`), and run plan → tasks → implement → review → evidence on branch
  `auto/<key>` with no questions. Only hard stops interrupt; the human's next gate is VERIFY.
  Same quality gates as large. Never pick this mode yourself.
- Say which you think it is and why, in the intent's last question. **The human decides.**
  Every commit under an intent carries the trailer `Intent: I-<key>`.

## Rules for the assistant (§1)

1. Work only on the stage you were asked for, then stop at the next gate that needs a person.
   Human-owned text: the human has the last word, you write only what they confirmed.
   AI-owned text: you write it, they review it at the gate.
2. Every artifact starts with `Derived from: <artifact> v<n>`.
3. Before implementation, read the architecture guide's §1.1 and cite its rule IDs in the plan.
4. During a large change `WIP.md` is the fence: implement it in order; anything outside it is a
   proposal written in `WIP.md`, not code.
5. Don't create files, abstractions or endpoints the spec doesn't need; list them under "Deferred".
6. If a task can't be done without breaking a spec or rule, stop (below); a workaround hides the
   conflict, a stop surfaces it while it is cheap.
7. Done is mechanical: the project's `Done commands:` from `AGENTS.md` (lint, typecheck, import
   rules, tests), the task's checks and `specfirst.py check`. Say which you ran.
8. Never modify a spec while implementing it; write a change request under it and stop.
   Exception: a spec with `Approved by: ai` in an autonomous run is revised in place (§3.9).

## Hard stops (§1.1)

These end the run in any stage and any autonomy mode. On a stop: revert uncommitted changes,
append `STOP T# <date> G# — <reason>` to the `WIP.md` log, touch nothing else, wait for a person.

- **G1** A rule exception or ADR is needed. Draft the ADR as `proposed`; never set `accepted`.
- **G2** A change would break a non-negotiable of the architecture guide or the import rules. Revert.
- **G3** A new dependency the plan doesn't list.
- **G4** The spec cannot be met as written. Write the change request; never edit the spec.
- **G5** Out of fence: files outside the plan's touched layers, or something the task didn't ask for.
- **G6** A check fails twice after one tier escalation.
- **G7** A spike changes the plan.
- **G8** Scope grows: more than ten tasks, a task must be split, review yields more than three
  fix tasks, or the run budget in `WIP.md` is spent.
- **G9** A new layer or top-level package (autonomous runs).

In an autonomous run: G4 → revise the spec (`Version` +1, `REVISED` line, `REVISE` log line)
unless it contradicts the intent; G5/G7 → update the plan (`REPLAN` log line); G3 fires for any
dependency not in the manifest and not named in the intent. **Resume:** after the human resolves
a stop and says `resume`, append `RESUME T# <date> — <decision>` and continue in the same mode.

## Artifacts (§2, naming §2.1)

```
docs/intents/I-<key>.md   Raw intent (human), Structured intent, Open questions, Triage (AI)
docs/specs/S-<key>.md     behaviour, contracts, acceptance criteria, Autonomy. ≤ 2 pages
docs/plans/P-<key>.md     layer placement, decisions, new dependencies, risks, deferred. ≤ 1 page
docs/adr/ADR-###.md       decisions and rule exceptions, sequential (or a section of the guide)
docs/evals/E-<key>.json   eval sets, where the project has a model
docs/learnings.md         dated notes feeding back into the guides
WIP.md                    task list, review section and log while a large change is built. ≤ 10 tasks
```

`<key>` is `YYMMDDHHMM-<slug>`. When you create the intent, take the timestamp from the clock
(`date +%y%m%d%H%M`), never from memory, and propose the slug from the human's text; the human
may change it until the intent is frozen. The spec and plan reuse the key and change only the
prefix: never give them a new timestamp or slug (NAME-1..3, NAME-6). Too big for
a cap → split the scope. [scripts/specfirst.py](scripts/specfirst.py): `init` creates this
layout and an `AGENTS.md` stub (needs `python3`, whatever the project's language); `check` validates every artifact and `WIP.md` against the
templates and is part of Done (put it in pre-commit or CI).

## Which stage, and what to read first (§3)

| You are asked | Stage | Read first | Produce | Gate |
|---|---|---|---|---|
| "New intent: <text>" | INTENT | [§3.1](references/stage-intent.md), [intent.md](templates/intent.md) | the file, text verbatim; read-back, interview, triage | human's `go` |
| "Process I-<key>" | INTENT | same | read-back, interview, triage | human's `go` |
| "I-<key> go, autonomous" | AUTONOMOUS RUN | [§3.9](references/stage-autonomous.md), then each stage's file as you reach it | branch `auto/<key>`, spec with assumptions, plan, `WIP.md`, commits, review, evidence | human at VERIFY |
| "Resume" after a STOP | the stopped stage | the `WIP.md` log, [§1.1](references/overview.md) | `RESUME` line, run continues | per mode |
| "Draft S-<key>" | SPEC | [§3.2](references/stage-spec.md), [spec.md](templates/spec.md) | spec after the spec interview; no code | human approves, sets `Autonomy` |
| "Plan S-<key>" | PLAN | [§3.3](references/stage-plan.md), [plan.md](templates/plan.md) | plan; G1 or G3 → say so, stop | self-check |
| "Cut tasks for P-<key>" | TASKS | [§3.4](references/stage-tasks.md), [wip.md](templates/wip.md) | `WIP.md` with tiers and checks | per `Autonomy` |
| "Implement WIP.md" | IMPLEMENT | [§3.5](references/stage-implement.md), [task-brief.md](templates/task-brief.md) | commits, ticks, log lines | all ticked, CI green |
| "Review WIP.md" | REVIEW | [§3.6](references/stage-review.md), [review-brief.md](templates/review-brief.md) | `## Review`, `R#` fix tasks | clean or fixed |
| "Verify S-<key>" | VERIFY | [§3.7](references/stage-verify.md) | AC → evidence table, spec implemented | human judges |
| "Learn from S-<key>" | LEARN | [§3.8](references/stage-learn.md) | dated learnings entry | — |

"S-<key> approved. Autonomy: run to verify" runs PLAN through REVIEW without waiting; only a
hard stop or VERIFY interrupts. Read the row's file and template before producing anything:
they carry the stage's rules and a worked example. Then:

- **INTENT** is one interview, at most three round trips: read back first ("did I understand
  you right?"), then gap questions with proposed answers and a `keep it open` option (large
  only), then triage and `go` in one question. Use the tool's question feature; never proceed
  on silence.
- **SPEC** is interviewed before approval, as deep as the spec needs: batches of four choices
  with a recommendation; answers become confirmed decisions in the spec; approval is the last
  question, with the project's `Autonomy default:` from `AGENTS.md` recommended.
- Cite the architecture guide's rule IDs in plans, task briefs and reviews.
- **IMPLEMENT**: one task at a time, one commit per task, one log line. With `Delegation: by
  tier` in `AGENTS.md`, each task runs in a fresh subagent on the model its tier allows
  (mechanical → smallest, standard → mid, judgement → the session's own), briefed with
  `task-brief.md`; a rule scan follows each commit; a check failing twice escalates one tier
  once, then G6. The `specfirst-implementer` agent does this (Claude Code subagent or Copilot
  custom agent); pass the model for the tier where the tool allows it. With
  `Delegation: off` (the default) the session does every task itself.
- **REVIEW**: a subagent that implemented nothing, briefed with `review-brief.md`; it writes the
  `Fence:`, `Rules read:` and `Spec:` map lines even when clean, then findings tagged
  `fence | rule | spec` with `file:line`; blocking ones become `R#` tasks, re-reviewed.
  The `specfirst-reviewer` agent does this (Claude Code subagent or Copilot custom agent).
- **VERIFY**: one `- AC-n` evidence row per acceptance criterion under `## Verify` in `WIP.md`;
  a `manual` row names who checked it and when.
- Never resolve a stop; relay it. Never edit an approved spec.

Chat assistants suit intent, spec and plan; coding agents suit tasks, implementation and review.
Don't write a spec with the repository open as your source: it will describe the code that
exists.
