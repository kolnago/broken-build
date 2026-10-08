# Spec-first guide — §3.6 REVIEW

One stage of the workflow: its purpose, template, rules and a worked example. Rules for the assistant, hard stops, artifacts and naming: [overview.md](overview.md); the stage index is at its end. Templates: [../templates/](../templates/).

---

### 3.6 REVIEW

**Purpose.** Look at the whole change with eyes that did not write it, before evidence is gathered. Per-task checks prove each task; the review proves the change — that nothing outside the fence slipped in, that no rule bent, and that the code can actually satisfy the spec.

**Who.** A fresh subagent on the standard tier, never the one that implemented a task; judgement-tier tasks are reviewed by the session's own model. Give it `templates/review-brief.md`: the full diff since the first task commit, the task texts, the spec's acceptance criteria, architecture guide §1.1 and the rule IDs the plan cites.

**What it checks, in order.**

1. **Fence.** Every hunk maps to a task. Anything else is out of fence: reverted, or moved to Proposals.
2. **Rules.** The guide's non-negotiables and the plan's rule IDs, file by file, including layer placement and imports.
3. **Spec.** Each acceptance criterion has code behind it and a test (or eval, where there is a model) that could prove it; identifiers match the spec's contracts.

**Output.** A `## Review` section in `WIP.md`, in this order: three map lines that show the work was done — `Fence:` (which files each task's hunks map to, and any unmapped hunk), `Rules read:` (§1.1 and the rule IDs the plan cites), `Spec:` (per AC, the test or eval that could prove it) — then one line per finding — `fence | rule | spec — file:line — what, and the task, rule ID or AC it concerns` — then a verdict (`clean` or `N blocking`) and the model used. The map lines are written even when the verdict is clean; `specfirst.py check` fails a verdict without them. Blocking findings become fix tasks `R1..` appended to `WIP.md`, each with checks and a tier, and are implemented per §3.5. More than three fix tasks is G8: the plan or the spec was wrong, not the code.

**Rules.**

- **REV-1** The reviewer is not the implementer. Fresh context, the brief only. A model reviewing its own reasoning finds what it already believed.
- **REV-2** Findings are tagged `fence`, `rule` or `spec`, each with a location and the task, rule ID or AC it concerns. An untagged finding is an opinion, and opinions go to Proposals. A verdict without the `Fence:` and `Spec:` map lines is an opinion too: a clean review shows what it mapped, so a reader can check it.
- **REV-3** `fence` and `rule` findings block. `spec` findings block when an AC has no code or no test behind it; otherwise they are noted for verify.
- **REV-4** The review section stays in `WIP.md`. A person reads it at verify together with the evidence table; it is how "just read the log" is possible.

**Gate → VERIFY.** Verdict `clean`, or every `R#` ticked and the re-review clean. CI green.

