# adk-bricks

My preferences for building Google ADK software with an AI assistant, kept minimal. Software is
composed from small bricks (tools, agents, workflows, skills, MCP servers, Python components);
the rules cover only what crosses a brick's edge. Google supplies the ADK API reference (the
`google-adk-reference` plugin and the adk.dev docs); this plugin holds only what is mine. The
`agents-cli` command is not used: projects run on `adk` and `uv`.

| Skill | Use it for |
|---|---|
| `charter` | the working procedure, the principles (P1–P6), the brick contract (B1–B8), strict, free and mixed trust, the folder for each kind, and a one-page recipe per kind under `references/` |

## Status

Draft, started 2026-10-03 beside `python-kit` and `adk-kit`, which stay as they are for the
projects that use them. Superseded on 2026-10-07 by `adk-modules`, which keeps the brick contract
and puts domain modules above it; this plugin stays as it is for the project built on it. The charter exists, and its repository shape was proven with a sample
repository ([kolnago/bricks-v1](https://github.com/kolnago/bricks-v1), private): bricks with offline tests, agents runnable by `adk`, and one
multi-stage image serving the agents and a React frontend that draws A2UI surfaces, and evals
beside each agent. Since 0.6.0 an app serves only the bricks it names and the routes its
frontend calls, keeps no session route and caps the request size, after a code review of the
first app built from the recipe found ADK's whole developer server exposed. Since 0.7.0 a brick
may hold parts, bricks in the same shape inside its folder that only the owner imports (B8), after
a second project put two features' agents in one flat folder and one workflow importing another's
helpers; the sample's `scripts/check_bricks.py` checks B8 with the rest of the contract. Next, in
this order:

1. A Cloud Run deployment of the sample image, then A2UI user actions and model-written layout.
2. The ADK gotchas and the offline testing helpers that Google's reference does not cover, carried
   over from `adk-kit`.
3. A light workflow, with the intent as the log.

## Use in a project

```bash
claude plugin install google-adk-reference@kolnago-plugins --scope project
claude plugin install adk-bricks@kolnago-plugins --scope project
```

Then name the charter in the project's `AGENTS.md`: "This repository follows the `adk-bricks`
charter."

Optionally add the ADK docs MCP server, which lets the assistant search and read adk.dev live
(nothing to keep updated; it needs network access):

```bash
claude mcp add adk-docs --scope project --transport stdio -- uvx --from mcpdoc --with "mcp<2" mcpdoc --urls AgentDevelopmentKit:https://adk.dev/llms.txt --transport stdio
```

The docs describe the latest ADK, so the installed package stays the final check (P5).

## Maintaining the charter

These rules are for whoever edits the skill, so they live here and not in the skill itself.

- `SKILL.md` stays under 120 lines. Adding a rule means showing what went wrong without it (P4).
- IDs keep their meaning. A retired rule keeps its number with a note.
- A recipe is written from something that ran. What the sample has not proven is named in the
  skill's last paragraph and stays there until it is.
- The sample is [kolnago/bricks-v1](https://github.com/kolnago/bricks-v1); it was verified on
  `google-adk` 2.11.0. When a rule changes, change the sample in the same step.
