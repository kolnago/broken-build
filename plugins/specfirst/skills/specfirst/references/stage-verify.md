# Spec-first guide — §3.7 VERIFY

One stage of the workflow: its purpose, template, rules and a worked example. Rules for the assistant, hard stops, artifacts and naming: [overview.md](overview.md); the stage index is at its end. Templates: [../templates/](../templates/).

---

### 3.7 VERIFY

**Purpose.** Prove the spec, not the code.

**Checklist, per acceptance criterion.**

| AC tag | Evidence required |
|---|---|
| `unit` / `contract` | Test name that covers it, linked in the PR |
| `integration` / `e2e` | Test run against the test database or environment, output attached |
| `eval` | Projects with a model: eval report with case IDs, pass/fail, model and prompt version |
| `metric` | Number from a test run, an eval run or staging telemetry against the threshold |
| `manual` | Who checked it, when, on what (commit, build, device), and what they saw |

**Rules.**

- **VFY-1** The evidence table lives in `WIP.md` under `## Verify`, one row per acceptance criterion: `- AC-n  <tag>: <test name | eval case | who checked it, when (a date), on what, what they saw>`. It sits next to the review and the log, survives the PR, and the PR description links to it. `specfirst.py check` fails an implemented spec whose AC has no row, and a `manual` row without a date. When the change is retired and `WIP.md` goes idle, the LEARN stage copies the table under the spec as `## Evidence`, so it is not lost.
- **VFY-2** Where the project has evals, a report records model name, prompt file hash and the version of the framework that ran it. Evals are not reproducible without them.
- **VFY-3** A failing check is fixed in what it checks, as a new task: the code for a test; the prompt, a tool description or the data the model is given, in that order, for an `eval`. Never by loosening the test, the threshold or the verifier.
- **VFY-4** When verification passes, the spec is marked `Status: implemented` with the commit hash. The spec and the code now agree; that is the point of the whole exercise. After that commit the spec's behaviour is frozen: `specfirst.py check` warns when a later commit changes it, and the fix is to bump `Version` or supersede. A commit that bumps `Version:`, or changes only the `Status:` line (recording the hash), lines under `## Change requests`, or blank lines, does not count.
- **VFY-5** A spec with `Approved by: ai` (autonomous run, §3.9) is judged with its evidence: the human reads `Read-back` and `Assumptions made` first, then the revisions and the log, then the evidence, and chooses accept, take it over, or discard (§3.9). Only accept marks it implemented; the assistant never merges `auto/<key>`.

