# Spec-First Development with AI Assistants

| | |
|---|---|
| **Version** | 2.14 (draft) |
| **Date** | 2026-10-06 |
| **Sibling of** | the project's architecture guide (the *what*), named in its `AGENTS.md`. This document is the *how*. A project without a guide starts one from [../templates/architecture-guide.md](../templates/architecture-guide.md) |
| **Examples** | one change followed through every stage: a CSV export of the order list in a layered web application (domain, services, storage, api, ui). The rules are the same in any language and framework; only the layer names and the Done commands differ |
| **Audience** | Engineers and AI coding assistants (Claude Code, GitHub Copilot, Codex) |

---

## Contents

The guide is split by section; `§` numbers are the guide's own and stay valid across files.

- §0 Why this document exists · §1 Rules for AI coding assistants · §1.1 Hard stops (G1..G9), resuming · §2 Artifacts · §2.1 Naming (NAME-1..8) · §2.2 Two workflows, and the autonomous run — this file
- §3.1 INTENT (INT-1..4: create from chat, read-back interview) — [stage-intent.md](stage-intent.md)
- §3.2 SPEC (SPEC-1..7, the spec interview) — [stage-spec.md](stage-spec.md)
- §3.3 PLAN (PLAN-1..6) — [stage-plan.md](stage-plan.md)
- §3.4 TASKS (TASK-1..8) — [stage-tasks.md](stage-tasks.md)
- §3.5 IMPLEMENT (IMPL-1..8, delegation by tier) — [stage-implement.md](stage-implement.md)
- §3.6 REVIEW (REV-1..4) — [stage-review.md](stage-review.md)
- §3.7 VERIFY (VFY-1..5) — [stage-verify.md](stage-verify.md)
- §3.8 LEARN (LRN-1..4) — [stage-learn.md](stage-learn.md)
- §3.9 Autonomous run (AUTO-1..5: a large change from intent `go` to VERIFY with no person in between) — [stage-autonomous.md](stage-autonomous.md)
- §4 Where the LLM helps in development · §5 Prompts · §6 Anti-patterns · §7 Minimal tooling (`specfirst.py`) · §8 Change log — [appendix.md](appendix.md)

Rule IDs here are the workflow's own. `DOM-n`, `SVC-n`, `API-n`, `P-n` and other IDs cited inside the examples belong to the example project's architecture guide; your project cites its own.

---

## 0. Why this document exists

Vibe coding is asking an assistant to "add X", accepting what appears, and asking for the next thing. It is fast for an hour and expensive for a month: nobody can say what the system is supposed to do, tests describe the code rather than the intent, and every change risks a rule in the architecture guide because the assistant never saw the rule.

Spec-first inverts the order. Words first, code last, and each stage produces a small artifact that the next stage consumes. The artifacts are short. The discipline is in the gates between them, not in document length.

The workflow for a large change:

```
INTENT → SPEC → PLAN → TASKS → IMPLEMENT → REVIEW → VERIFY → LEARN
```

Each arrow is a gate. Three of them need a person: reviewing the intent, approving the spec (and choosing how far the assistant runs on its own), and judging the evidence at the end. The others are self-checks that pass unless a hard stop (§1.1) fires. AI assistants draft; humans approve. Small changes do not go through it at all (§2.2) — the chain is for work where nobody can yet say what "correct" means. A large change can also run autonomously (§3.9): the human chooses it at the intent's `go`, the assistant approves its own spec, and the person's next gate is VERIFY.

---

## 1. Rules for AI coding assistants

1. Work only on the stage you were asked for. Asked for a spec, produce a spec and stop. Do not "also implement it".
2. Every stage artifact starts by naming the artifact it derives from (`Derived from: docs/specs/S-2609111020-order-export.md v2`).
3. Read the architecture guide §1.1 before any implementation task. Cite rule IDs in the plan (`DOM-2`, `API-3`).
4. During a large change, `WIP.md` is the task list: implement all of it, in order, without waiting between tasks, unless a hard stop (§1.1) fires. Anything outside it is a proposal, written as a comment in `WIP.md`, not code.
5. Do not create files, abstractions, or endpoints the spec does not require. When in doubt, leave it out and note it under "Deferred".
6. When a task cannot be done without breaking a spec or a rule, say so rather than working around it. The conflict is information: it means the plan and the code have come apart (§3.5).
7. Definition of done is mechanical: the project's own lint, typecheck, import-rule and test commands, listed once in `AGENTS.md` as `Done commands:`, and `specfirst.py check`, all green, plus the task's acceptance checks. Say which ones you ran. `check` warns while `Done commands:` is missing or still the placeholder. A kind of check the language or project does not have is left out of the list, not faked.
8. Never modify a spec while implementing it. Propose the change in `docs/specs/<id>.md` under "Change requests" and stop. The one exception is a spec the assistant approved itself in an autonomous run (`Approved by: ai`): it is revised in place with a version bump, logged (§3.9).

**The architecture guide.** The workflow needs one, however short: plans cite its rule IDs, the rule scan and the review read its §1.1, and G2 has nothing to protect without it. It can be a file in the repository or a skill; `AGENTS.md` says which. A project that has none writes one page from `templates/architecture-guide.md` (what the application is, the non-negotiables, the layers with a few rules each, the Done commands) as its first small change, before the first large one.

**Ownership.** Every section of every artifact is one of two kinds. *Human-owned* means the human has the last word: the assistant may draft or propose, and writes only what the human confirmed. *AI-owned* means the assistant writes it and the human reviews it at the gate. Neither means the other side may not help; it says who decides.

### 1.1 Hard stops

These end the run in any stage and any autonomy mode. They are not failures of the assistant; each one means the plan and reality have come apart, and that is information a person needs before more code is written. On a hard stop: leave the working tree clean (revert uncommitted changes), append one line to the `WIP.md` log — `STOP T# <date> G# — <reason>` — touch nothing else, and wait.

- **G1 Rule exception or ADR needed.** The assistant may draft the ADR, always with `Status: proposed`. It never sets `accepted`; only a person does.
- **G2 Non-negotiable or import rule broken.** A change would violate architecture guide §1.1 or fail the project's import-rule check. Revert, stop.
- **G3 New dependency** not listed in the plan (IMPL-1).
- **G4 Spec cannot be met** as written. Write the change request under the spec, never edit the spec.
- **G5 Out of fence.** A task needs files outside the plan's touched layers, or something the task did not ask for.
- **G6 Check fails twice** after one tier escalation (IMPL-7).
- **G7 Spike changes the plan.**
- **G8 Scope grows.** The task list would exceed ten, a task must be split (IMPL-4), review produces more than three fix tasks, or the run budget in `WIP.md` is spent.
- **G9 New layer or top-level package** (autonomous runs, §3.9). The plan or a task would add a layer to the architecture or a new top-level package. A module or subpackage inside an existing layer is not G9. In a supervised run the human sees this at spec approval or the task list; in an autonomous run nobody would, so it stops.

In an autonomous run (§3.9) the assistant owns the spec and the plan, so G4 becomes a logged spec revision, G5 and G7 become logged plan updates, and G3 fires for any dependency the intent does not name, even one the assistant's own plan lists.

**Resuming.** After a stop the human resolves what the stop line names and says `resume`. The assistant appends `RESUME T# <date> — <what the human decided>` to the `WIP.md` log and continues in the same autonomy mode from the stopped task. A decision that changes the goal is a new intent, not a resume.

Why a list rather than judgement: a stop that depends on the assistant noticing is a stop that happens sometimes. A numbered condition can be cited in the log, checked by a reviewer, and tested.

---

## 2. Artifacts and where they live

```
docs/
├── intents/    I-<key>.md  Raw intent (human), Structured intent, Open questions, Triage (AI)
├── specs/      S-<key>.md   behaviour, contracts, acceptance criteria — no implementation
├── plans/      P-<key>.md   how the spec maps onto the architecture; decisions; risks
├── adr/        ADR-###.md architecture decisions (rule exceptions, tech choices)
├── evals/      E-<key>.json eval sets, only where the project has a model: the acceptance tests for its behaviour
└── learnings.md           dated notes: what surprised us, what to change in the guides
WIP.md                     the task list while a large change is being built
```

An intent's key is unique and never reused; its spec and plan take the same key (§2.1). Only ADRs are numbered sequentially. An intent leads to a commit or to one spec, as named in its `Triage` (an intent that needs more is split, NAME-4); one spec produces exactly one plan and one `WIP.md` task list at a time.

Sizes are capped on purpose: `Structured intent` ≤ 10 lines and `Raw intent` is not capped, spec ≤ 2 pages, plan ≤ 1 page, `WIP.md` ≤ 10 tasks. If an artifact needs more, the scope is too big; split it.

---

### 2.1 Naming

Every chain shares one key, set by the intent. The intent is named `I-YYMMDDHHMM-<slug>.md`; its spec and plan take the same key with their own prefix:

```
docs/intents/I-2609201337-kickoff.md
docs/specs/S-2609201337-kickoff.md
docs/plans/P-2609201337-kickoff.md
```

| Part | Rule |
|---|---|
| Prefix | `I` intent, `S` spec, `P` plan, `E` eval set |
| `YYMMDDHHMM` | When the intent was created, local time, to the minute. `2609201337` is 20 Sep 2026, 13:37 |
| `<slug>` | Lowercase ASCII kebab-case, no diacritics, at most five words |

The file name without `.md` is the artifact's ID. Sorting a folder by name sorts it by creation time, and nobody has to know the next free number.

- **NAME-1** The human names the intent when creating it. If an assistant ever creates an intent, it takes the timestamp from the clock (`date +%y%m%d%H%M`), never from memory.
- **NAME-2** Keys are unique and never reused. If a key is taken, use the next free minute.
- **NAME-3** A spec and a plan never get a new timestamp or slug: they take the intent's key and change only the prefix. `Derived from:` is still written, so the chain is explicit in the file too.
- **NAME-4** One intent leads to at most one spec and one plan. If `Triage` finds that an intent needs more than one spec, the intent is split into several intents, each with its own key, before it is frozen.
- **NAME-5** References always use the full ID, slug included: `S-2609201337-kickoff`, never `S-2609201337` alone.
- **NAME-6** The key may change while the human is still writing the intent; it is frozen with `Raw intent`. After that, no file in the chain is renamed. A new version of a spec keeps its name and bumps `Version:`.
- **NAME-7** A superseding intent gets a new key, and so do its spec and plan. The old spec is marked `Status: superseded`.
- **NAME-8** ADRs keep sequential numbers (`ADR-017`, …): they are few, cited by number in the guides, and not part of an intent chain. A project keeps them as files in `docs/adr/` or as a section of its architecture guide; it says which in `AGENTS.md`.

Projects that started with sequential IDs (`S-003`) keep them; `specfirst.py check` warns rather than fails on those. The examples in this guide use keyed IDs from here on.

---

### 2.2 Two workflows

Every change starts as an intent, small or large: `docs/intents/` sorted by key is the log of
what was done to the application and why, and the human does not write code, so the intent is
also the only place their words are kept verbatim. What differs is how much comes after it.

An intent is a problem a person owns, frozen in their words. A spec is a behaviour a test
owns, written so it can be proven. To place a sentence, ask who would have erred if it turned out
wrong: "that is not what I asked for" belongs to the intent, "that is what I asked for, but it
behaves wrongly" to the spec. Intent questions confirm the request; solution choices wait for the
spec interview.

**Small change.** A fix, a tooling tweak, a dependency bump, a wording change — anything whose
correct behaviour is already obvious or already written down in an approved spec. The intent
gets a read-back and a `go`, nothing more: no gap questions unless one is blocking, no spec, no
plan. The assistant does it, runs the definition of done, commits with the `Intent:` trailer and
writes the commit hash into the intent's `Closed by:`; when a test or check proved it, an
optional `**Checks:**` line under `Triage` names it. One round trip for the human.

**Large change.** New behaviour: a new screen, a new endpoint, a new report, anything where
two people given the same sentence would build different things. The
intent is interviewed, then a spec is agreed, then the chain runs.

**When it is not obvious:** if explaining the change takes more than about three sentences, or if
you could not write the test first because you do not yet know what "correct" means, it is large.

- **The human picks the workflow.** The AI says which one it thinks this is and why, in the
  intent's last question; the human decides. Guessing large when it is small costs ceremony,
  guessing small when it is large costs a rewrite.
- **A large change keeps intent and spec separate.** The intent's read-back confirms the request
  was understood; the spec's read-back confirms the behaviour still matches it.
- **Every commit under an intent carries the trailer `Intent: I-<key>`**, small or large, so
  `git log` and the intents folder tell the same story. An intent is closed by a commit hash
  (small) or by its spec reaching `Status: implemented` (large). `specfirst.py check` warns when
  a `Closed by:` commit is missing or carries no trailer; `specfirst.py log --trailers` lists
  the mismatches in both directions.
- **The architecture guide's rule groups that do not apply to this project** are listed once in
  `AGENTS.md` (`Rule groups not applicable: STO, SEC-1..3 (no data store, no identity)`), with
  a reason, so specs cite the line instead of restating it; `check` warns when a spec's `Rules
  that apply` cites an excluded group.

**Large, autonomous.** A large change the human wants built without being asked along the way.
The intent is interviewed as usual; its last question offers `go, autonomous` next to `go`. The
assistant then writes the spec (with every unasked decision under `Assumptions made`), approves
it itself (`Approved by: ai`), plans, cuts tasks, implements, reviews and fills the evidence
table on branch `auto/<key>`, stopping only on a hard stop. The quality gates are those of the
large workflow; only the questions are gone. The human judges spec and evidence together at
VERIFY. §3.9 has the rules.

---

## 3. The stages

One file per stage, each with purpose, template, rules and a worked example. Read the stage you were asked for before producing anything.

| § | Stage | File | Gate after it |
|---|---|---|---|
| 3.1 | INTENT | [stage-intent.md](stage-intent.md) | human reviews, says go |
| 3.2 | SPEC | [stage-spec.md](stage-spec.md) | human approves, sets `Autonomy` |
| 3.3 | PLAN | [stage-plan.md](stage-plan.md) | self-check: no exceptions, no new dependencies |
| 3.4 | TASKS | [stage-tasks.md](stage-tasks.md) | per `Autonomy`: human glance or continue |
| 3.5 | IMPLEMENT | [stage-implement.md](stage-implement.md) | all ticked, CI green |
| 3.6 | REVIEW | [stage-review.md](stage-review.md) | verdict clean, or `R#` fixed and re-reviewed |
| 3.7 | VERIFY | [stage-verify.md](stage-verify.md) | human judges evidence, review, log |
| 3.8 | LEARN | [stage-learn.md](stage-learn.md) | — |
| 3.9 | Autonomous run | [stage-autonomous.md](stage-autonomous.md) | human at VERIFY only; hard stops interrupt |
