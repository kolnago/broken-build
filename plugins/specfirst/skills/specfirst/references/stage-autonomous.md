# Spec-first guide — §3.9 AUTONOMOUS RUN

How a large change runs from the intent's `go` to VERIFY with no person in between. Rules for the assistant, hard stops, artifacts and naming: [overview.md](overview.md); the stage index is at its end. Templates: [../templates/](../templates/).

---

### 3.9 Autonomous run

**Purpose.** Sometimes the human wants a large change built without being asked along the way: a proof of concept, a spike that grew, work where being surprised at the end is cheaper than being interrupted. The autonomous run is the large workflow with the spec gate moved to the end. The assistant writes the spec, the plan and `WIP.md`, builds, reviews and gathers the evidence; the human judges everything together at VERIFY. Every artifact of the large workflow is still written, so the run can be read afterwards exactly like a supervised one.

**What it is not.** It is not a third size. The intent is triaged `large` as usual; autonomy is how the large change runs. A small change has no reason to use it.

**How it starts.** In the intent's last question (§3.1 step 4) a large intent offers `go` · `go, autonomous` · `let me edit first` · `stop here`. Only the human picks `go, autonomous`; the assistant may recommend it but never assumes it. On that answer the intent's `Triage` gets `**Autonomy:** autonomous` and the intent freezes as usual. The intent interview itself is unchanged: read-back and gap questions happen before `go`, because they are the only point where the human's reading is confirmed.

**What runs, in order.**

| Stage | In an autonomous run |
|---|---|
| Branch | Before writing anything, create and switch to `auto/<key>`. Every artifact and commit of the run lands there; merging is the human's decision at VERIFY |
| SPEC | No spec interview (SPEC-7 does not apply). The assistant drafts the spec, fills every gap it would have asked about with an entry under `Assumptions made`, and sets `Status: approved`, `Approved by: ai`, `Autonomy: autonomous`. A blocking open question (SPEC-3) is resolved by an assumption, never left open |
| PLAN | As §3.3. The self-check still applies: an ADR (G1), a new dependency (G3) or a new layer or top-level package (G9) stops the run here, before any code |
| TASKS | As §3.4; no pause at the task list. Checkpoints become `CHECKPOINT` log lines |
| IMPLEMENT | As §3.5: tiered subagents, Done per task, rule scan per commit (IMPL-8) |
| REVIEW | As §3.6: fresh-context reviewer, `R#` fix tasks |
| VERIFY | The assistant fills the evidence table (§3.7) and stops. This is the human's gate |
| LEARN | As §3.8, after the human's verdict |

**Hard stops in an autonomous run.** §1.1 applies, with these differences, because the assistant now owns the spec and the plan:

- **Unchanged:** G1 (ADR or rule exception), G2 (non-negotiable or import rule), G6 (check fails twice), G8 (scope or budget).
- **G3 is stricter.** A dependency stops the run unless it is already in the project's dependency manifest or is named in `Raw intent` or `Clarifications`. Listing it in the assistant's own plan does not authorise it. Name the libraries you expect in the intent if you want the run to use them.
- **G9 applies** (§1.1): a new layer or a new top-level package. A new module or subpackage inside an existing layer does not stop the run.
- **G4 becomes a revision.** When the spec cannot be met as written, the assistant revises it: `Version` +1, one line under `Change requests` — `REVISED v<n> <date> — <what changed and why>` — and a `REVISE` line in the `WIP.md` log. A revision that would contradict `Raw intent`, `Clarifications` or the intent's `Out of scope` is not allowed: that is G4 and the run stops.
- **G5 and G7 become plan updates.** The fence is the assistant's own plan, so work outside it or a spike that changes it updates the plan instead of stopping: `Touched layers` or the decision edited in `P-<key>`, one `REPLAN` line in the log. Anything a task did not ask for is still a proposal, not code, so the review keeps meaning something. G9, G1 and G3 still fire on whatever the new plan contains.

**Resuming after a stop.** The human resolves what the stop line names (accepts the ADR, names the dependency in `Clarifications`, decides the scope) and says `resume`. The assistant appends `RESUME T# <date> — <what the human decided>` to the log and continues in the same mode from where it stopped. A decision that changes the goal is not a resume: it is a new intent that supersedes this one.

**Rules.**

- **AUTO-1** Only the human chooses `go, autonomous`, in the intent's last question. The spec records the choice as `Autonomy: autonomous` with `Approved by: ai`, and the two always appear together.
- **AUTO-2** The spec is written from `Raw intent` and `Clarifications` only, never from the code. Everything the assistant decided that they do not state is an entry under `Assumptions made`, so the human can find every decision taken on their behalf in one place.
- **AUTO-3** The run works on branch `auto/<key>` and never merges it.
- **AUTO-4** Spec revisions (G4) and plan updates (G5, G7) are logged where they happen and in the `WIP.md` log. A silent change to an AI-approved artifact is the same defect as a silent change to a human-approved one.
- **AUTO-5** Quality gates are those of the large workflow, unchanged: Done (the project's lint, typecheck, import rules and tests, plus `specfirst.py check`), the rule scan per commit, the fresh-context review and the evidence table. Autonomy removes questions, not checks.

**Gate → done (human, at VERIFY).** The human reads, in this order: the spec's `Read-back` and `Assumptions made`, its `Change requests` revisions, the `WIP.md` log (`STOP`, `REVISE`, `REPLAN`, `CHECKPOINT` lines), the review section, and the evidence table. Then one of:

- **accept** — the spec becomes `Status: implemented <hash>` as in VFY-4; the human merges `auto/<key>`. `Approved by: ai` stays: it is the record of how the spec was made.
- **take it over** — the spec goes back to `Status: draft` with `Version` +1, `Approved by` and `Autonomy` are cleared, and the normal spec interview (§3.2) runs on it, assumptions first. The branch is kept as a reference implementation; the chain continues as a supervised large change.
- **discard** — the branch is deleted, the spec is marked `superseded`, and the intent stays open or is superseded by a new one.

**Worked example (log of a run).**

```markdown
## Log
- T1 done 2610011012 tier=mechanical model=haiku checks=storage tests commit=4be1c02 — capped order query
- REPLAN 2610011030 — T3 needs the existing permissions check in api/; added api to Touched layers
- T2 done 2610011041 tier=judgement model=opus checks=domain tests commit=9d0a7e1 — export row formatting
- STOP T3 2610011055 G3 — needs a streaming CSV library for large exports; not in the dependency manifest, not named in the intent
- RESUME T3 2610011320 — human added Clarification Q5: the streaming library is allowed
- REVISE S v2 2610011402 — AC-6 limit 10 000 → 50 000 rows; one month of orders is 30 000
- T3 done 2610011415 tier=standard model=sonnet checks=api contract tests commit=c51f2aa — export endpoint
```
