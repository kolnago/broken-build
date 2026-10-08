# Spec-first guide — §3.8 LEARN

One stage of the workflow: its purpose, template, rules and a worked example. Rules for the assistant, hard stops, artifacts and naming: [overview.md](overview.md); the stage index is at its end. Templates: [../templates/](../templates/).

---

### 3.8 LEARN

**Purpose.** Feed reality back into the guides, so the next spec starts smarter.

After each spec ships, add a dated entry to `docs/learnings.md`:

```markdown
## 2026-09-12 — S-2609111020-order-export
- The accountant's spreadsheet read the file as Latin-1 until a byte-order mark was added. Decision: write the mark; AC-7 stays manual. (API-7 candidate)
- Assistant twice built the CSV inside the endpoint. API-2 in §1.1 was not enough; added an anti-pattern row.
- The web framework streams a response only from a generator; `# VERIFY` marker removed in the guide's §4, verified on the installed version.
```

**Rules.**

- **LRN-1** Every `# VERIFY` marker resolved during implementation is removed from the architecture guide in the same PR, with the version it was verified against.
- **LRN-2** A rule that assistants keep breaking gets a sharper wording or a CI check. Do not rely on repetition.
- **LRN-3** Learnings that change behaviour become a version bump in the relevant guide.
- **LRN-4** When `WIP.md` is retired, its `## Verify` rows are copied under the spec as `## Evidence`, so the evidence outlives the task list. Follow-ups listed under `Follow-ups` in the entry are proposals; `specfirst.py check` lists the ones no later intent picked up.

