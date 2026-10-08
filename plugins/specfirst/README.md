# specfirst

How I build applications with AI assistants, packaged once instead of copied into every project.
The workflow does not depend on a language or a framework: the same stages run a Python agent
app, a desktop app and a TypeScript or Go service. What differs per project is its architecture
guide and its Done commands, and both are named in the project's `AGENTS.md`.

| Part | What it is |
|---|---|
| skill `specfirst` | intent → spec → plan → tasks → implement → review → verify → learn; three human gates, hard stops, an optional autonomous run, optional tiered delegation, keyed naming, templates, `specfirst.py`. Guide v2.13; the change log is in `skills/specfirst/references/appendix.md` |
| `templates/architecture-guide.md` | a one-page architecture guide for a project that has none |
| `agents/` | two Claude Code subagents, `specfirst-implementer` and `specfirst-reviewer` |

Until v2.12 the skill lived in `python-kit`. It moved here on 2026-10-03 so that projects that
are not Python can use it; `python-kit` keeps `python-architecture`.

## The subagents

`specfirst-implementer` runs one `WIP.md` task from a filled `templates/task-brief.md`. With
`Delegation: by tier` in the project's `AGENTS.md` the IMPLEMENT stage spawns it per task on the
model the task's tier allows, so an expensive session spends its own tokens on judgement and
review. The default is `Delegation: off`: the session does every task itself and `Tier:` is a
risk label. `specfirst-reviewer` runs the REVIEW stage from a filled `review-brief.md` on a
change it did not write, on the standard tier.

| Tier | Model to pass when spawning | Typical tasks |
|---|---|---|
| mechanical | `haiku` | query files, repositories from an existing interface, fakes, fixtures, text and template edits, evidence table |
| standard | `sonnet` (the agents' default) | use cases, adapters, endpoints, contract tests |
| judgement | the session's own model, or do it in the session | calculations and business rules, security-sensitive code, data migrations, spikes |

Other tools ignore `agents/`; the skill tells the session to run the tasks itself when it has no
subagents.

## How a large change runs

A person acts three times: reviewing the processed intent, approving the spec, and judging the
evidence at the end. At spec approval the person sets `Autonomy`: `show tasks` adds one more
pause at the task list, `run to verify` lets plan, tasks, implementation and review run without
waiting. Everything in between is a self-check that passes unless one of the hard stops G1–G9
fires (a rule exception or ADR needed, a non-negotiable broken, an unlisted dependency, an
unmeetable spec, out-of-fence work, a check failing twice, a spike changing the plan, scope
growing, a new layer or top-level package). A stop leaves a clean tree and one `STOP` line in
the `WIP.md` log. The log, the review section and the evidence table are what the person reads
afterwards.

For a large change you want built without being asked along the way, answer the intent's last
question with `go, autonomous` (§3.9). The assistant then writes the spec with every decision it
took for you listed under `Assumptions made`, approves it itself (`Approved by: ai`), and runs
plan, tasks, implementation, review and evidence on branch `auto/<key>` with the same quality
gates. Only a hard stop interrupts; after one, `resume` continues. You judge spec and evidence
together at VERIFY: accept, take it over as a supervised change, or discard.

Every change starts as an intent, so `docs/intents/` is the log of the application. A small
change is one round trip: read-back, `go`, commit with the `Intent:` trailer, hash into
`Closed by:`. A large one is interviewed at intent and again, deeper, at spec, always as choices
with a recommended answer, so the human confirms rather than types.

Artifacts are keyed by the intent: `I-2609201337-kickoff.md`, `S-2609201337-kickoff.md`,
`P-2609201337-kickoff.md`. The assistant proposes the key and slug from the chat sentence; spec
and plan reuse the key.

## What the project brings

- **An architecture guide**, a file in the repository or a skill, named in `AGENTS.md`. Its
  `§1.1` non-negotiables and its rule IDs are what plans, briefs and reviews cite. A project
  without one writes a page from `skills/specfirst/templates/architecture-guide.md` first. A
  Python project can start from `python-architecture` in `python-kit` instead; an ADK app uses
  `adk-architecture` in `adk-kit`.
- **Done commands**: its own lint, typecheck, import-rule and test commands, listed in
  `AGENTS.md` as `Done commands:`. The workflow adds `specfirst.py check` to them.
- **`python3` on the machine**, for the check script only. The script uses the standard library
  and reads Markdown, `AGENTS.md` and git history; it never runs or parses the project's code.

## Install

```bash
claude plugin marketplace add kolnago/claude-plugins --scope project
claude plugin install specfirst@kolnago-plugins --scope project
```

Other tools: copy or symlink `skills/specfirst` into the tool's skills directory.

## Per project

Set up the docs layout once and keep it checked:

```bash
python3 <plugin-dir>/skills/specfirst/scripts/specfirst.py init
python3 <plugin-dir>/skills/specfirst/scripts/specfirst.py check
```

`init` creates `docs/{intents,specs,plans,adr,evals}`, `docs/learnings.md` and an `AGENTS.md`
stub that names the architecture guide and sets the project's `Done commands:`,
`Autonomy default:`, `Delegation:` and `Rule groups not applicable:`. `log` prints every intent
in key order with its size, status and what closed it: the application's changelog;
`log --trailers` cross-checks git's `Intent:` trailers against it. `check` validates every
artifact and `WIP.md` against the templates (keys, `Derived from`, `Status`, `Autonomy`, tagged
ACs, plan sections, the fence, the review's map lines, the `## Verify` rows, the log and its
commits), prints what's next, and exits non-zero on a failure; add it to pre-commit or CI.
With the plugin installed, the plugin directory is wherever
`claude plugin details specfirst@kolnago-plugins` says.

A project that set the script path while the skill was in `python-kit` (a Makefile or CI step
searching for `python-kit/skills/specfirst/scripts/specfirst.py`) needs the path changed to
`specfirst/skills/specfirst/scripts/specfirst.py`, and `specfirst@kolnago-plugins` installed.

Keep the project's own decisions in the project (its architecture guide, ADRs, specs, learnings)
and a short `AGENTS.md` with its always-on rules; `CLAUDE.md` can point to it.

## Updating

- `skills/specfirst/references/` is the source of truth for the workflow. Carry changes to
  projects, not the other way. The guide is split by section with its own `§` numbers kept:
  `overview.md` (§0–2: rules, hard stops, artifacts, naming, a file index), `stage-<name>.md`
  for §3.1–3.9, `appendix.md` for §4–8 including the change log. `SKILL.md` routes each request
  to one stage file, so a session loads only the stage it works.
- The worked examples follow one change, a CSV export of an order list in a layered web
  application. Keep them free of any one language or framework.
- The script's own tests are in `skills/specfirst/tests/`; run them with
  `pytest plugins/specfirst/skills/specfirst/tests`.
- Bump `version` in `plugin.json` when the skill changes.
