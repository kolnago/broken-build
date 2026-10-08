# I-<key> <title>
<!-- <key> = YYMMDDHHMM-<slug>: the minute this was created (date +%y%m%d%H%M) and at most five lowercase ASCII words. Slug and title may change until the freeze (NAME-1, NAME-6). -->

## Raw intent
<!-- HUMAN-OWNED: the human has the last word. Written by the human, or pasted verbatim from chat (INT-1). Never rephrased by the assistant. Freezes on the human's go. -->


### Clarifications
<!-- Interview answers the human confirmed, one per line: "Q# → answer". Human-owned once confirmed (INT-3). -->
-

### Context
<!-- AI-OWNED, optional. What the human pointed at: attachments, screenshots, files, the chat proposal they accepted. Facts only; the reading goes in Structured intent. Delete when there is none. -->
-

## Structured intent
<!-- AI-OWNED. Only from Raw intent + Clarifications (INT-4). Unstated: "—" plus an open question. ≤ 10 lines. -->

**Read as:** <the reading the assistant took, one sentence>
**Not read as:** <plausible readings it did not take>
**Who:**
**Wants:**
**Why now:**
**Out of scope:**
**Success looks like:**
**Constraints:** the project's architecture guide applies.

## Open questions
<!-- AI-OWNED. One line per gap in Raw intent: not yet asked, or kept open by the human. -->
-

## Triage
<!-- AI-OWNED. From the wording only: no judgement on merit. The human decides in the last interview question. -->

**Size:** small | large
**Reason:**
**Next artifact:** commit | S-<same key>   <!-- more than one spec needed → split the intent (NAME-4) -->
**Checks:** <small only, optional: the tests or checks that prove it, e.g. `<test command> <test name>; e2e "…"`>
**Autonomy:** — | autonomous   <!-- large only; set when the human answers `go, autonomous` (§3.9) -->
**Closed by:** <empty until closed; then the commit hash(es) (small) or the spec's implemented commit (large)>
