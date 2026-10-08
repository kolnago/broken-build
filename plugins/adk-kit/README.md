# adk-kit

Google ADK agent apps where numbers must be trustworthy, packaged once instead of copied into
every project. The workflow that builds them lives in the `specfirst` plugin; this plugin holds what is
specific to ADK.

| Skill | Use it for | Source |
|---|---|---|
| `adk-architecture` | layers, figures with provenance, turn ledger, derive tool, number verification, the shell pattern, rule IDs | adk-next `adk-architecture.md` v2.0 |
| `a2ui-surfaces` | agent answers as A2UI surfaces rendered in React (experimental) | a2ui-v1 prototype |
| `adk-a2ui-integration` | wiring A2UI into an app: route choice, pins, vendored schemas, server templates, `emit_ui`, actions, SSE or A2A transport, Lit/React bootstrap, security review, restricted-environment deployment (experimental) | research pass 2026-10-02 |
| `adk-workflows` | ADK 2.x graph workflows: nodes, routing, loops, fan-out/join, dynamic nodes, `RequestInput`, task mode, tools, MCP, node-as-tool; 10 tested examples | adk2-dev 0.2.0 |
| `adk-app-runtime` | App/Runner wiring, services and state scopes, plugins and callbacks, resilience, telemetry, `get_fast_api_app`, deployment in restricted perimeters | adk2-dev 0.2.0 |
| `adk-testing` | offline pytest with a scripted model, framework canaries, `adk test` golden replay, `adk eval` criteria | adk2-dev 0.2.0 |

`adk-architecture` is an adopted instance of the `python-architecture` template in `python-kit`:
the shared rules (framework-free core, exact money, no implicit today, calculators, ports with
fakes, SQL in files, testing by layer) plus what only an LLM app with numbers needs — figures,
the turn ledger, `derive`, verification at the exit, and the ADK 2.0 bindings.

Each skill is a plain [Agent Skills](https://agentskills.io) folder (`SKILL.md` with `name` and
`description` only, relative links, no tool-specific features), so the same folders work in
Claude Code, GitHub Copilot, Codex and Google Antigravity. `.claude-plugin/plugin.json` is the
Claude Code packaging on top.

`adk-workflows`, `adk-app-runtime` and `adk-testing` are framework-general (no number rules): they complement
`google-agents-cli` (Google's scaffold, adk-code, workflow, deploy and eval skills) with tested
examples, test helpers, canaries and restricted-environment runtime guidance. They came from the
`adk2-dev` kit, verified on `google-adk` 2.11.0 and derived from the Apache-2.0 `google/adk-python`
docs, samples and `.agents/skills`.

## Install

Install `specfirst` first: the spec-first workflow, its templates, check script and the
implementer and reviewer subagents are there. `python-kit` is optional; it holds the
`python-architecture` template that `adk-architecture` follows.

```bash
claude plugin marketplace add kolnago/claude-plugins --scope project
claude plugin install specfirst@kolnago-plugins --scope project
claude plugin install adk-kit@kolnago-plugins --scope project
```

Other tools: copy or symlink the folders under `skills/` into the tool's skills directory.

## Per project

`AGENTS.md` names `adk-architecture` as the project's architecture guide, so `specfirst` plans,
briefs and reviews cite its rule IDs (`P1`, `CORE-6`, `TOOL-5`, `VER-2`). Keep the project's own
decisions in the project (`docs/adr/`, specs, learnings).

## Updating

The `references/` files are copies of the source guides. When a guide changes, copy the changed
part again and bump `version` in `plugin.json`:

- `adk-architecture/references/` holds the architecture guide split by section (`overview.md`
  §0–5, `core.md` §6, `data.md` §7, `tools-and-shell.md` §8, `verification.md` §9,
  `state-errors-config.md` §10–12, `testing-enforcement.md` §13–14,
  `checklists-antipatterns.md` §15–18). Section numbers are the guide's own, so paste a changed
  section into its file; the index in `SKILL.md` says which file holds which section.
- `a2ui-surfaces/references/` holds the ADR and code excerpts from the a2ui-v1 prototype. The
  excerpts are not a runnable package; `SKILL.md` lists what they leave out.
- `adk-a2ui-integration/references/` holds the developer guide (`guide.md`, with sources) and
  starting-shape code. It defers to `a2ui-surfaces` for what a surface may contain; its `emit_ui`
  accepts layout only and the backend writes the data model.
- The `examples/` folders of `adk-workflows`, `adk-app-runtime` and `adk-testing` are runnable. `adk-testing/examples/test_examples.py` exercises the
  `adk-workflows` examples offline (13 example tests plus 4 canaries that pin framework
  behaviours); run it on every ADK upgrade:

  ```bash
  cd plugins/adk-kit/skills/adk-testing/examples
  uv run --with "google-adk==2.11.0" --with pytest --with pytest-asyncio pytest -q   # 17 passed
  ```

## Verified against

Each skill states the versions it was verified against in its own `SKILL.md`; this table is the
overview. The versions differ because the skills come from different projects. Re-verify on
upgrades and update both the skill and this table.

| Skill | `google-adk` | Other pins | What "verified" means | Not verified |
|---|---|---|---|---|
| `adk-architecture` | 2.8.0 (what adk-next pins); §8.3–8.5 on 2.11.0 | — | the items the guide marks as verified | everything marked `# VERIFY` in the references |
| `a2ui-surfaces` | 2.9.2 (prototype); backend on 2.11.0 | `a2ui-agent-sdk` 0.6.0 (prototype), backend also on 0.7.0; protocol v0.9; `@a2ui/react` 0.11.1, `@a2ui/web_core` 0.11.0 | prototype ran with a real model and browser; backend re-run offline by `scripts/test_a2ui_surfaces.py` | React side on newer `@a2ui/*`; a real model on 2.11; cost figures |
| `adk-a2ui-integration` | 2.10.0; guide §2, §4.4, §4.7 on 2.11.0 | `a2ui-agent-sdk` 0.7.0, `a2a-sdk` 0.3.x, protocol v0.9.1, `@a2ui/*` 0.12.0 | imports, signatures and schemas against the installed packages | anything end to end (no model, no browser) |
| `adk-workflows`, `adk-app-runtime`, `adk-testing` | 2.11.0 | — | 17 offline tests in `adk-testing/examples` | behaviour with a real model |

Re-run the `a2ui-surfaces` backend check from the repository root (19 tests, on SDK 0.6.0 or
0.7.0):

```bash
uv run --with "google-adk==2.11.0" --with "a2ui-agent-sdk==0.7.0" --with pytest pytest -q scripts/test_a2ui_surfaces.py
```
