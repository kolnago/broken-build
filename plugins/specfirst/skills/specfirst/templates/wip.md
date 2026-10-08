# WIP — S-<key> v<n> / P-<key>
Autonomy: <show tasks | run to verify | autonomous, from the spec>
Rules: architecture guide §1.1. Only tasks below. Propose anything else as a comment here.
Done means: <the project's Done commands from AGENTS.md: lint, typecheck, import rules, tests>, specfirst.py check green + task checks.
Budget: 20 subagent runs.   <!-- only with `Delegation: by tier` in AGENTS.md; drop the line otherwise -->
Mode: run-to-completion, one task per fresh subagent on the model its Tier allows (or the session itself, with `Delegation: off`). Hard stops G1–G9 (specfirst §1.1) end the run. Per task: checks → commit "T#: …" → tick → log line.
Every commit carries the trailer `Intent: I-<key>`.
Branch: <current | auto/<key> for an autonomous run (§3.9)>

- [ ] T1 <layer/module>: <what>.
      Tier: mechanical | standard | judgement
      Checks: <tests that prove it>
<!-- ⏸ CHECKPOINT — <what the human reviews here>; waits on: <repo>#<PR> when the run is parked on something outside this repository -->

## Proposals (not authorised)

## Review
<!-- written by the REVIEW pass, exactly this shape (REV-2): -->
<!-- - Fence: T1 ← <files>; T2 ← <files>; … (no unmapped hunks | unmapped: <files>) -->
<!-- - Rules read: §1.1, <rule IDs the plan cites>, layer table -->
<!-- - Spec: AC-1 ← <test or eval>; AC-2 ← …; AC-n manual -->
<!-- - <fence | rule | spec> — <file:line> — <what>, concerns <T# | rule ID | AC-#>   (one per finding) -->
<!-- - Verdict: clean | <N> blocking -->
<!-- - Model: <model> -->

## Verify
<!-- written by the VERIFY pass, one row per acceptance criterion (VFY-1): -->
<!-- - AC-1  unit: <test name> -->
<!-- - AC-2  manual: <who> checked it on <YYYY-MM-DD> on <commit>, saw <what> -->

## Log
<!-- T# done <date> tier=<tier> model=<model> checks=<what ran> commit=<hash> — <one clause> -->
<!-- CHECKPOINT <date> — <summary>          (under Autonomy: run to verify) -->
<!-- STOP T# <date> G# — <reason> -->
<!-- RESUME T# <date> — <what the human decided> -->
<!-- REVISE S v<n> <date> — <what changed in the spec, why>   (autonomous run only) -->
<!-- REPLAN <date> — <what changed in the plan, why>             (autonomous run only) -->
