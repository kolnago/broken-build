# Spec-first guide — §3.1 INTENT

One stage of the workflow: its purpose, template, rules and a worked example. Rules for the assistant, hard stops, artifacts and naming: [overview.md](overview.md); the stage index is at its end. Templates: [../templates/](../templates/).

---

### 3.1 INTENT

**Purpose.** Verify that the assistant understood what the human wants, before anyone proposes a solution. A prompt that reads fine to the person who wrote it is often ambiguous to everyone else; this stage is where that is found, while a correction costs one sentence rather than a rejected spec.

**Who.** `Raw intent` is human-owned: the human has the last word, and the assistant writes only what the human confirmed. The rest of the file is AI-owned and reviewed at the gate. Assistants challenge; they do not decide.

**The loop, in one interview.** The whole stage is one conversation with at most three round trips.

1. **Create.** On *"new intent: <text>"* the assistant creates `docs/intents/I-<key>.md` from the template: the key from the clock (`date +%y%m%d%H%M`), a slug and title proposed from the text, and the human's words pasted **verbatim** as `Raw intent`. The human may change slug and title until the freeze (NAME-6). On *"process I-<key>"* the file already exists and this step is skipped.
2. **Read back first.** The assistant fills `Structured intent` — only from `Raw intent` — including `Read as:` (the reading it took) and `Not read as:` (plausible readings it did not take). Then it asks one question: *did I understand you right?* with the restatement and the answers `yes` · `partly` · `no`. `Partly` or `no` takes a correction: the human retypes, or picks a reading from `Not read as`, or accepts a rewording the assistant proposes. A confirmed correction is written into `Raw intent` under `Clarifications`, and the assistant refills its sections and asks again. The loop ends on `yes`.
3. **Ask the gaps** (large changes; for a small one only a blocking question is asked). Remaining gaps become questions, at most four in one batch, each with two to four proposed answers, a recommended one, and always `keep it open`. Questions come only from what `Raw intent` does not say, never from what the assistant would like to build. Answers the human picks are human-confirmed: recorded under `Clarifications`; `Structured intent` is refilled from `Raw intent` plus `Clarifications`. Anything kept open stays in `Open questions`.
4. **Triage and go, one question.** The assistant states small or large and why (from the wording only, no judgement on merit) and asks: *freeze and proceed?* with `go` (freeze; produce the `Next artifact`) · `go, autonomous` (large only: freeze, then run spec to verify with no further questions, §3.9) · `let me edit first` (the human edits the file; the assistant refills and asks once more) · `stop here`. On `go`, the key and `Raw intent` are **frozen** and the assistant produces what `Triage` names. Large: the spec. Large with `go, autonomous`: `**Autonomy:** autonomous` in `Triage`, then the autonomous run (§3.9). Small: the change itself — done, definition of done run, one commit with the trailer `Intent: I-<key>` (several when the change is bigger than the human's `small` suggests; list them all), and the hash written into `Closed by:`. When a test or check proved it, `**Checks:**` under `Triage` names it, so a small change leaves a trail too. The intent then reads as one line of the application's log.

Use the tool's question feature when it has one (Claude Code and Copilot both do); otherwise ask as a numbered list in chat. Never proceed on silence.

**Rules.**

- **INT-1** An intent created from chat carries the human's words verbatim as `Raw intent`; the assistant never rephrases them there and adds nothing there. What the human pointed at — an attachment, a screenshot, a file, the chat proposal they accepted — goes under `### Context`, an optional AI-owned subsection of facts. Its own reading goes in `Structured intent`, its proposed rewordings into the interview.
- **INT-2** The read-back question comes before any gap question. Nothing is asked about a request until the reading of it is confirmed.
- **INT-3** Interview answers are choices with a recommendation and a `keep it open` option; at most four questions per batch, at most three batches. Only a confirmed answer is written down, and it is written under `Clarifications`, not into the human's original sentence.
- **INT-4** `Structured intent` contains only what `Raw intent` and `Clarifications` state. Reading the repository is allowed — an assistant with the repo open cannot unsee it — but nothing learned there may be added here. What the code already does is not what was asked for. Unstated items are `—` plus an open question; a plausible invented "who" reads exactly like a real one three weeks later.

**No judgement on the merit or feasibility of the idea.** That belongs to the spec and the plan. `Triage` is the assistant's reading of the wording; the human decides.

**IDs.** `I-YYMMDDHHMM-<slug>` per §2.1 (NAME-1..8). The key is frozen with `Raw intent`. If the **goal** changes after freezing, create a new intent with `Supersedes: I-<key>` and add `Superseded by: I-<key>` to the old one; that link is the only edit allowed on a frozen intent. If a **detail** changes, file a spec change request instead.

**Template.** Ownership is marked per section; the example shows a confirmed clarification and an unstated field left as `—`.

```markdown
# I-2609111020-order-export Export the order list for the accountant

## Raw intent
<!-- HUMAN-OWNED: the human has the last word. Written by the human, or pasted verbatim from chat. The key freezes with it. -->
support keeps getting asked for order lists for the accountant. takes them half an hour of
copy-paste from the orders screen. want a button that downloads what the screen shows as a
file she can open in a spreadsheet. read-only, no changes to orders and no new reports.

### Clarifications
<!-- Confirmed interview answers, one per line. Human-owned once confirmed. -->
- Q2 → CSV with a header row; the columns the screen shows.

## Structured intent
<!-- AI-OWNED. Only from Raw intent + Clarifications. Unstated: "—" plus an open question. ≤ 10 lines. -->

**Read as:** A download of the order list as currently filtered on screen, as a CSV file.
**Not read as:** A scheduled report sent by email; a new reporting screen.
**Who:** Support staff, on behalf of the accountant.
**Wants:** One button on the orders screen that downloads what the screen shows as a file a spreadsheet opens.
**Why now:** Today this takes half an hour of copy-paste per request.
**Out of scope:** Changing orders, new reports.
**Success looks like:** —
**Constraints:** architecture guide applies. Read-only. Only what the screen shows.

## Open questions
<!-- AI-OWNED. One line per gap in Raw intent, kept open by the human or not yet asked. -->
- Q1 What counts as success? The raw intent does not say how many orders one export must handle or how fast. (kept open)

## Triage
<!-- AI-OWNED. From the wording only: no judgement on merit. The human decides. -->

**Size:** large
**Reason:** New behaviour: a download with a file format two people would build differently.
**Next artifact:** S-2609111020-order-export
**Autonomy:** —
**Closed by:** <commit hash when small; the spec's implemented commit when large>
```

**Gate → next artifact.** The human's `go` (or `go, autonomous`) in the last interview question is the gate. The assistant then produces what `Triage` names. Unresolved questions stay in the intent as open questions; they do not move into the spec.
