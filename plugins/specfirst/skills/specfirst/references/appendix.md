# Spec-first guide — §4–8 Roles, prompts, anti-patterns, tooling, change log

Back matter of the guide. Rules and gates: [overview.md](overview.md); stages: one file each, indexed there.

---

## 4. Where the LLM helps in *development* (and where it does not)

Use a model where breadth and judgement help and a script where a rule can be checked mechanically; that holds for the process as much as for the application.

| Stage | Assistant role | Human role |
|---|---|---|
| Intent | Create the file from chat; read back; interview gaps with proposed answers; say small or large and why | Say it in one sentence; answer by choosing; confirm the reading; go |
| Spec | Interview every open point as choices; draft criteria; spot untestable sentences. Autonomous run: draft without interview, list assumptions, approve | Answer by choosing; approve; set autonomy. Autonomous run: nothing until VERIFY |
| Plan | Propose layer placement, list options with trade-offs, flag rule conflicts | Only when G1 or G3 fires: accept an ADR or a dependency |
| Tasks | Cut tasks, order them inside-out, attach checks and tiers | Glance at the fence, if `show tasks` |
| Implement | Write tests and code inside the fence | Read the log; act on hard stops |
| Review | Fresh-context pass: fence, rules, spec; fix tasks | Read the review section |
| Verify | Run the tests (and evals, where there is a model), fill the evidence table | Judge whether evidence is sufficient |
| Learn | Draft the learnings entry | Decide what changes |

Use a chat assistant (this kind of conversation) for intent, spec, and plan, where breadth and pushback matter. Use a coding agent (Claude Code, Copilot CLI) for tasks and implementation, where the fence matters. Do not ask a coding agent to write the spec while it has the repo open; it will describe the code that exists.

---

## 5. Prompts that keep sessions on the rails

**New intent (one sentence is enough)**

> New intent: <what you want, in your own words>. The assistant creates the file, reads back, interviews, triages, and asks to go.

**Intent processing**

> Process I-<key>: fill Structured intent, Open questions, and Triage from Raw intent only — nothing from the code, however obvious. Say whether it looks small or large and why. Don't judge the idea. Stop.

**Intent go**

> I-<key> go: proceed per Triage.

**Intent go, autonomous (large only)**

> I-<key> go, autonomous: write the spec with assumptions listed, approve it yourself, and run to verify on auto/<key>. Stop only on a hard stop.

**Resume after a stop**

> Resume: <what I decided, e.g. ADR-017 accepted / rapidfuzz allowed, added as Clarification Q5>.

**Spec drafting (chat assistant)**

> Read I-2609111020-order-export. Draft S-<key> using the template in the specfirst guide §3.2. Every acceptance criterion must be testable and tagged. List open questions separately. Do not propose implementation.

**Plan drafting (chat or coding agent, read-only)**

> Read S-2609111020-order-export (approved) and the architecture guide. Produce P-2609111020-order-export per §3.3: touched layers with rule IDs, decisions, risks, deferred. If any rule must be broken, say so and stop. No code.

**Task cutting (coding agent, read-only)**

> Read P-2609111020-order-export. Write WIP.md per §3.4: inside-out order, one layer per task, checks per task, spikes first. Do not implement.

**Implementation (coding agent)**

> Read the architecture guide §1.1 and WIP.md. Implement every unticked task in order. Per task: failing test first where the task has logic a test can pin down, then the code, then the task's checks plus the Done commands from AGENTS.md, then one commit "T#: …", then tick the box and add a log line. Tell me rather than working around it if the task conflicts with the spec or a rule, if it needs something the task did not ask for, or if a check keeps failing or a spike changes the plan. Pause at any ⏸ CHECKPOINT and summarise what is done. Delegate each task to a fresh subagent on the model its Tier allows, using templates/task-brief.md; do judgement-tier tasks yourself.

**Spec approval (human, one line)**

> S-2609111020-order-export approved. Autonomy: run to verify.

**Review (coding agent, fresh context)**

> Review the diff since the first T# commit against WIP.md task texts, S-2609111020-order-export acceptance criteria and architecture guide §1.1. Tag every finding fence, rule or spec with file:line. Write the Review section in WIP.md and append R# fix tasks for blocking findings. Do not fix anything yourself.

**Change request (either)**

> While implementing T5, S-2609111020-order-export AC-4 cannot be met because [reason]. Do not change the spec. Write a change request under S-2609111020-order-export "Change requests" with two options and stop.

---

## 6. Anti-patterns

| Anti-pattern | Symptom | Fix |
|---|---|---|
| Spec written from the code | Criteria describe functions, not behaviour | Rewrite from the intent; SPEC-4 |
| Plan skipped | Layers wrong, rule IDs missing, assistant invents structure | Always plan; PLAN-1 |
| `WIP.md` as a wish list | 25 tasks, half vague | Cap at 10, split the spec |
| "Also fixed a few things" | Diff larger than the task | Revert; IMPL-3 |
| Green tests, red spec | Tests pass but AC has no evidence | VFY-1 evidence table |
| Loosening a check to make it pass | Green CI, wrong behaviour | VFY-3 |
| Batch run with no per-task commits | One unreviewable diff | Commit per task (§3.5) |
| Prompt edited inline during implementation (projects with a model) | Untracked behaviour change | TASK-4 |
| Learnings kept in chat | Same mistake next spec | LRN-1..3 |
| Reviewer is the implementer | Review finds nothing, ever | REV-1 |
| Assistant accepts its own ADR | Rule exceptions nobody chose | G1, PLAN-2 |
| Autonomous run without assumptions | Spec reads as if every decision was yours | AUTO-2: every unasked decision is listed |
| Autonomy picked for a change you must get right first time | Rework after VERIFY | Use `run to verify`: you approve the spec, the rest still runs alone |

---

## 7. Minimal tooling

None of this needs a framework. The skill ships `scripts/specfirst.py`. It needs `python3` on the machine (standard library only) and reads nothing but Markdown, `AGENTS.md` and git history, so the project itself can be in any language:

- `specfirst.py init` creates the `docs/` layout of §2, `docs/learnings.md` and an `AGENTS.md`
  stub with the always-on rules, including the `Done commands:` line to fill. Idempotent; run it once per project.
- `specfirst.py check` is the mechanical half of the gates. It verifies that every intent, spec,
  plan and ADR has the shape its template requires (IDs match file names, `Derived from`,
  `Status`, `Version`, `Autonomy` on approved specs, `Approved by: ai` exactly when `Autonomy: autonomous`, tagged acceptance criteria, the plan's
  sections), that `WIP.md` keeps its fence (header names an approved spec and an existing plan;
  at most ten tasks and three fix tasks; every task has a tier and checks; at most two
  checkpoints; a budget line under `Delegation: by tier`; a log line for every ticked task),
  that `Autonomy: autonomous` and `Approved by: ai` come together (AUTO-1), that a review
  verdict comes with its `Fence:` and `Spec:` map lines (REV-2), that an implemented spec has a
  `## Verify` row per AC with a date on manual ones (VFY-1), lists `STOP` lines no `RESUME`
  resolved, prints the "what's next" view (approved specs without a plan, plans without a
  `WIP.md`, the next open task, a checkpoint parked on another repository, learnings follow-ups
  no intent picked up), and warns when an autonomous change is not on its `auto/<key>` branch,
  when an implemented spec changed after its recorded commit
  without a version bump, when a `Closed by:` or log commit is missing or carries no `Intent:`
  trailer, when two ticked tasks share a commit, when a spec cites a rule group `AGENTS.md`
  excludes, when `AGENTS.md` has no `Done commands:`, and when a delegated tier ran on the session. Non-zero exit on any failure, so it
  runs in pre-commit or CI and is part of "done". Files are read as UTF-8 on every platform.
- `specfirst.py log --trailers` cross-checks git: commits whose `Intent:` trailer names no
  intent file, and closing commits without the trailer.
- `tests/test_specfirst.py` next to the script runs with pytest (standard library plus
  `tmp_path`); it builds temporary projects and git repositories, so a change to the script is
  proven in the plugin, not in an app that vendors it.

What it does not do is judge content: whether a read-back is right, whether an AC is the right
one, whether a tier is honest. Those are the human gates and the review.

---

## 8. Change log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-10 | Initial draft: seven-stage workflow, templates, gates, assistant rules |
| 1.1 | 2026-09-11 | Run-to-completion implementation: assistants work the whole task list, gated per task by checks and commits, with explicit stop conditions and at most two checkpoints |
| 1.2 | 2026-09-11 | Risk tiers (§2.1); every request starts as an intent whose `Raw intent` is human-owned and never edited by the AI; the AI restates understanding from that text alone and with no judgement on merit, and triages a provisional tier; the human's go is required at every tier; intent IDs are free-form and frozen with `Raw intent` after review; specs open with a Read-back the human approves first (SPEC-5) |
| 1.3 | 2026-09-11 | Intent stage no longer forbids reading the repository — the rule was unenforceable for an assistant with the repo open. What survives is the part that mattered: `Structured intent` carries only what `Raw intent` states |
| 2.0 | 2026-09-11 | Two workflows replace the four risk tiers: small changes are done and committed, large ones get an intent and a spec. The mechanical tier floor, the tier field and the go-gate on small changes are gone; the stop conditions become three things worth mentioning rather than five prohibitions. The point of the process is an organised record, not a restraint on the assistant |
| 2.1 | 2026-09-26 | VERIFY-stage rules renamed `VER-n` → `VFY-n`: the architecture guide already uses `VER-n` for number verification and plans cite both |
| 2.2 | 2026-09-26 | Tasks carry a `Tier:` (TASK-7) and implementation delegates each task to a fresh subagent on the model the tier allows, one at a time (IMPL-6, IMPL-7 escalation); `templates/task-brief.md` is the handoff |
| 2.3 | 2026-09-26 | Hard stops G1..G8 in one list (§1.1); autonomy chosen at spec approval; plan gate becomes a self-check (PLAN-5); post-task rule scan (IMPL-8); REVIEW stage with a fresh-context reviewer (REV-1..4); log line format and run budget in `WIP.md` |
| 2.4 | 2026-09-26 | `scripts/specfirst.py init` and `check` (§7): the docs layout and the mechanical half of the gates as a tool; `check` is part of done |
| 2.14 | 2026-10-06 | One-line rule for intent versus spec (§2.2): an intent is a problem a person owns, frozen in their words; a spec is a behaviour a test owns, written so it can be proven; the "who would have erred" test places a sentence; solution choices wait for the spec interview. No rule-ID changes |
| 2.13 | 2026-10-03 | Language-neutral, and its own plugin (`specfirst`, moved out of `python-kit`): Done is the project's own commands, named in `AGENTS.md` as `Done commands:` (§1 rule 7); IMPL-1 speaks of the dependency manifest; TASK-3 and TASK-7 name layers and tiers by role, not by Python folder; VFY-2 and VFY-3 cover evals only where there is a model; the worked examples follow one neutral change (order export) instead of the ADK analyst agent; `templates/architecture-guide.md` is a one-page guide for a project that has none (§1). `check` warns when `AGENTS.md` has no `Done commands:`; the worked task list passes `check` (the spike names its check, TASK-2). No gate or rule ID changed |
| 2.12 | 2026-10-01 | Tool-neutral wording: the implementer and reviewer agents are named as Claude Code subagents or Copilot custom agents; the project instructions file is `AGENTS.md` (or `CLAUDE.md` / `copilot-instructions.md` pointing to it). No rule changes |
| 2.11 | 2026-10-01 | Autonomous run (§3.9, AUTO-1..5): `go, autonomous` at the intent runs a large change to VERIFY with no further questions; the assistant approves its own spec (`Approved by: ai`) with every unasked decision under `Assumptions made`, works on `auto/<key>`; G4 becomes a logged spec revision and G5/G7 logged plan updates; G3 fires for any dependency the intent does not name; new hard stop G9 (new layer or top-level package); `RESUME` after a stop; VFY-5; `log` marks autonomous intents |
| 2.10 | 2026-10-01 | VFY-4 states what `check` counts as a change after implementation; appending under `## Change requests` no longer counts (only the `Status:` line and a `Version:` bump did) |
| 2.9 | 2026-09-28 | From the Intentor review: `Delegation: off | by tier` in `AGENTS.md`, off by default (IMPL); a review verdict needs its `Fence:` and `Spec:` map lines (REV-2); the evidence table lives in `WIP.md` under `## Verify` and `check` enforces it (VFY-1); optional `### Context` under Raw intent (INT-1) and `**Checks:**` for small changes (§2.2); `## External repositories` in the plan (PLAN-6), `waits on:` checkpoints and TASK-8 for tasks elsewhere; TASK-1 allows one task across core and its caller when neither is green alone; `Rule groups not applicable:` in `AGENTS.md`; `Autonomy:` in the WIP header; `check` verifies `Closed by:` and log commits and their trailers, shared commits, learnings follow-ups; `log --trailers`; UTF-8 everywhere; tests in the plugin |
| 2.8 | 2026-09-26 | `manual` AC tag for what only a person can judge, with its evidence row (SPEC-1, VFY); an idle `WIP.md` with no tasks passes the check between changes (TASK-5) |
| 2.7 | 2026-09-26 | Every change starts as an intent; the intents folder is the application's log; small changes close on a commit with the `Intent:` trailer and `Closed by:`. The spec interview (SPEC-7) with confirmed decisions and approval as the last question; `Autonomy default:` in `AGENTS.md`. `specfirst.py log` |
| 2.6 | 2026-09-26 | INTENT is one interview: create from chat verbatim, read back first, gap questions with proposed answers, triage and go in the last question (INT-1..4); `Clarifications` block; ownership defined once in §1 |
| 2.5 | 2026-09-26 | Framework-agnostic: the architecture guide is referred to by role and named in the project's `AGENTS.md`. From `prijmy-specfirst.md` 1.2: keyed naming `I-/S-/P-YYMMDDHHMM-slug` (§2.1, NAME-1..8), SPEC-6 (values with sources), PLAN-5 packaging note, `e2e` AC tag. Examples re-keyed |

Intents written before v1.2 use the older shape: a single structured block, with no `Raw intent`
and no `Triage`. They are not retrofitted — there is no raw text to recover, and rewriting a
frozen intent to match a later template is exactly what the freezing rule forbids. Read them as
history.

Changes to these guides and to the project instructions file (`AGENTS.md`, or `CLAUDE.md` /
Copilot's `copilot-instructions.md` pointing to it) are constitutional: they are made directly, not
through an intent, because the process cannot authorise amendments to itself.

