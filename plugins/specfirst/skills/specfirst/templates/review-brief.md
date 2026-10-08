# Review brief — S-<key> v<n> / P-<key> / WIP.md

You are reviewing a whole change you did not write. Find what the per-task checks cannot:
changes outside the fence, rules bent across files, acceptance criteria with nothing behind them.
Do not fix anything.

## Inputs
- Diff: `git diff <first T# commit>^..HEAD` (paste or let the reviewer run it)
- Task texts: every `T#` line from WIP.md, verbatim
- Acceptance criteria: from S-<key>, verbatim, with their tags
- Rules: the architecture guide's §1.1 and the rule IDs P-<key> cites per layer
- Contracts: the identifiers named under Contracts in S-<key>

## Check, in this order
1. Fence: does every hunk map to one task? List hunks that map to none.
2. Rules: per file, the guide's non-negotiables and the cited rule IDs; layer placement and imports.
3. Spec: per AC, the code that implements it and the test or eval that could prove it;
   identifiers match the contracts.

## Output (write into WIP.md under `## Review`, exactly this shape, even when clean)
- Fence: T1 ← <files>; T2 ← <files>; … (no unmapped hunks | unmapped: <files>)
- Rules read: §1.1, <the rule IDs the plan cites>, the layer table (imports checked per file)
- Spec: AC-1 ← <test or eval that could prove it>; AC-2 ← …; AC-n manual
- <fence | rule | spec> — <file:line> — <what>, concerns <T# | rule ID | AC-#>
- ...
- Verdict: clean | <N> blocking
- Model: <model>

The three map lines are the evidence for the verdict: a `clean` with no map is an opinion, and
`specfirst.py check` fails a review that has a verdict but no `Fence:` and `Spec:` lines.

Then, for each blocking finding, append one fix task to the list:
- [ ] R1 <layer/module>: <what to change>.
      Tier: <by content, same table as TASK-7>
      Checks: <what proves the fix>
More than three fix tasks: write them anyway, then STOP with G8; the plan or the spec was wrong.

Blocking: every `fence` and `rule` finding; a `spec` finding when an AC has no code or no test.
Untagged observations are opinions: put them under Proposals, not under Review.
