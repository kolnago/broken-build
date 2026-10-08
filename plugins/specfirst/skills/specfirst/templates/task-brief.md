# Task brief — T# of WIP.md (S-<key> v<n> / P-<key>)

You are implementing one task from an approved task list. Work only inside it.

## The task
<the T# line from WIP.md, verbatim, including Tier and Checks>

## What it serves
<the acceptance criteria from S-<key> this task contributes to, verbatim>

## Rules
- The architecture guide's §1.1 (the non-negotiables), pasted below or linked.
- The guide's section for this task's layer, pasted below or linked (the matching § or reference file of the project's guide).
- No new dependency (IMPL-1), no TODO without a task ID (IMPL-2), no refactoring neighbours (IMPL-3), expected values in tests from fixtures only (IMPL-5).

## Files
- Touches: <paths this task may change>
- Reads: <existing modules, ports, fixtures, golden files it must use>

## Procedure
1. If the task has logic a test can pin down (a calculation, a rule, a parser), write the failing test from the acceptance criterion first.
2. Write the code.
3. Run the task's checks, then the project's full checks (as WIP.md "Done means").
4. One commit named `T#: <task title>`; tick the box in WIP.md and append one log line.
5. Return the report below. Do not edit the spec, the plan, or any task text.

## Stop instead of working around it (hard stops, specfirst §1.1)
- G2 the change would break a non-negotiable or the import rules
- G3 it needs a dependency the plan does not list
- G4 the spec cannot be met as written
- G5 it needs files outside the fence, or something the task did not ask for
- G6 a check fails twice
- G7 a spike result changes the plan
- G9 it needs a new layer or a new top-level package
In an autonomous run (WIP.md `Branch: auto/<key>`) you still stop and report G4, G5 and G7; the session turns them into a spec revision or plan update instead of ending the run (§3.9). There G3 covers any dependency the intent does not name.
Leave the working tree clean (revert uncommitted changes), cite the G number, and report.

## Report (return exactly this shape)
- Task: T#  Status: done | stopped
- Commit: <hash or none>
- Files changed: <paths>
- Checks: <each check, pass/fail, and the failing output if any>
- Stop reason: <none | G# and one paragraph>
- Proposals: <none | one line each, for the Proposals section of WIP.md>
