# Spec-first guide — §3.5 IMPLEMENT

One stage of the workflow: its purpose, template, rules and a worked example. Rules for the assistant, hard stops, artifacts and naming: [overview.md](overview.md); the stage index is at its end. Templates: [../templates/](../templates/).

---

### 3.5 IMPLEMENT

**Purpose.** Produce the code the tasks describe, and nothing else.

**How to run an assistant session.** The assistant works the list to the end. The gate on each task is mechanical, not conversational.

**Per task.** Tests first where the task has logic a test can pin down (a calculation, a rule, a parser): write the failing test from the acceptance criterion, then the code. Then run the task's own checks plus the project's Done commands (lint, typecheck, import rules, tests, as `AGENTS.md` names them). Then one commit named for the task (`T4: …`), then tick the box and append one line to the `WIP.md` log. One task, one commit — a batch with a single diff cannot be reviewed against the task text.

**When to stop.** The hard stops in §1.1 apply. The ones this stage hits are G2 (rule broken), G3 (dependency), G4 (spec cannot be met), G5 (out of fence), G6 (check fails twice) and G7 (spike changes the plan). Stop rather than work around: each one means the plan and the code have come apart, and that is information.

**Checkpoints.** At a `⏸ CHECKPOINT` line, pause and report what the completed tasks produced, so the human can review before work depends on it. Resume on their word. With `Autonomy: run to verify` or `autonomous` a checkpoint does not pause: it writes a `CHECKPOINT` line to the log with the same summary, and the person reads it at verify.

**Who does the task: `Delegation:` in `AGENTS.md`.** The default is `off`: the session does every task itself, `Tier:` stays a label of how much judgement the task needs, and `WIP.md` needs no `Budget:` line. A solo developer on one model gains little from the ceremony below and loses the context that carries from task to task. With `Delegation: by tier` the rest of this paragraph applies, and `check` warns when a mechanical or standard task logs `model=session`.

**Fresh context per task, on the cheapest model that can do it (`Delegation: by tier`).** When the tool has subagents, the session is the orchestrator and each task runs in its own subagent, one at a time, in order. The session fills `templates/task-brief.md` — the task line, the acceptance criteria it serves, §1.1, the architecture reference file for the task's layer, the files it touches — and picks the model from the task's tier (TASK-7): mechanical → the smallest model, standard → the mid model, judgement → the session's own model, or the session does the task itself. The subagent commits, ticks the box and writes the log line, then returns the report shape from the brief. The session confirms the commit exists and the checks passed, and moves on. It does not re-review the diff (that is the human's review below) and it does not resolve a stop condition — it relays it. Two reasons this is worth the ceremony: a late task cannot drift on the reasoning of an early one, and the expensive model is spent on judgement, not on writing query files and fakes.

**When to go one task at a time anyway.** The first specs on a new codebase, changes to code the rest of the application trusts for correctness (money, permissions, data migrations), and any plan whose risks are still open. Cadence is a judgement about how much is unknown, not a fixed rule.

**Review.** Read each commit against its task text, not against "does it look reasonable". Anything not in the task is reverted or moved to Proposals.

**Rules.**

- **IMPL-1** No new dependency without a line in the plan. Changes to the dependency manifest (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, …) are reviewed like architecture.
- **IMPL-2** No commented-out code, no `TODO` without a task ID.
- **IMPL-3** Assistants do not refactor neighbours. "While I was here" is a proposal.
- **IMPL-4** A task that turns out larger than a sitting is split in `WIP.md` before continuing.
- **IMPL-5** Expected values in tests come from golden files or fixtures with provenance, never from the assistant's head.
- **IMPL-6** Delegated tasks run in a fresh context with only the brief; the subagent may not edit the spec, the plan or any task text, and reports proposals instead of making out-of-fence changes.
- **IMPL-7** A check that fails twice on a lower tier is rerun once on the next tier before the stop condition fires. The retry is cheap; hiding the failure is not — after the escalation, stop and say so (G6).
- **IMPL-8** After each commit, a rule scan: the session, or a subagent on the smallest model, reads the commit's diff against architecture guide §1.1 and the rule IDs the plan cites for that layer. A hit reverts the commit and stops (G2). Most rule breaks are visible in a diff — an inner layer importing a framework, business logic in an endpoint, a query assembled from input — and a scan on the cheapest model catches them for almost nothing, while the review (§3.6) does the whole-change pass.

**Gate → REVIEW.** All boxes ticked, CI green.

