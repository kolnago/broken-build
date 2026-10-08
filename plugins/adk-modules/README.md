# adk-modules

How I build Google ADK software with an AI assistant, organised by domain. A repository is cut
into **modules** named in the business's language (`exposure`, `investigation`,
`breaches/limit_overdraft`), each module holds its **bricks** by kind (models, ports,
calculators, tools, agents, ...), and **apps** are built from the bricks the modules export.
The rules cover what crosses a module's or a brick's edge; inside you are free.

This plugin groups three things that were separate before:

| Skill | Use it for |
|---|---|
| `charter` | the working procedure, the principles (P1–P6), the module contract (M1–M5), the brick contract (B1–B9), strict, free and mixed trust, the repository shape, a recipe per kind of brick under `references/`, and `scripts/check_modules.py`, which checks the contracts a linter cannot |
| `python-rules` | the Python rules an AI agent follows in such a repository: uv, ruff, mypy strict, Pydantic v2, pytest, errors, logging, async, security, dependencies, git; tagged MUST/SHOULD/MAY, with the profile that fits them to the module shape |
| `.mcp.json` | the `adk-docs` MCP server: the assistant searches and reads adk.dev live through `mcpdoc` (needs `uvx` and network access) |

Google's ADK API reference is not repeated here: install `google-adk-reference` beside this
plugin. The `agents-cli` command is not used; projects run on `adk` and `uv`.

## Status

Draft 0.1.0, started 2026-10-07 as the successor of `adk-bricks` (0.7), which stays as it is
for the project built on it.

What changed and why: a project with many breach types that share exposure calculations and
investigation methods got lost in a flat `bricks/<kind>/` tree. The kind of a brick says what
sort of thing it is, not what it is for. So the top level is now the domain, and the kind is a
convention inside each module. Two smaller changes came from the same project: visibility is
*declared* by what a module exports instead of being read off a folder path, and `__init__.py`
holds no implementation, so an editor tab, a traceback and a grep all name the brick.

What is proven and what is not:

- The brick-level recipes (model, port, calculator, tool, surface, callback, agent, workflow,
  skill, MCP server, scripted model, app) are carried over from `adk-bricks` 0.7, where they
  were verified on `google-adk` 2.11.0 against the sample `kolnago/bricks-v1` (private). Only
  their paths and file layout changed.
- The module level (M1–M5, B9, `check_modules.py`, the repository shape) is new ground: it has
  not yet been proven by a sample repository. The first project built on it is the proof; what
  it finds changes this plugin in the same step.

Next, in this order:

1. A sample repository in the module shape, with the check script in its CI.
2. The `adk-kit` material Google's reference does not cover (ADK gotchas, offline testing
   helpers), rewritten as recipes.
3. Cloud Run deployment of a sample app; A2UI user actions and model-written layout.

## Use in a project

```bash
claude plugin install google-adk-reference@kolnago-plugins --scope project
claude plugin install adk-modules@kolnago-plugins --scope project
```

Then name both skills in the project's `AGENTS.md`:

> This repository follows the `adk-modules` charter and its `python-rules`.

Copy `skills/charter/scripts/check_modules.py` into the repository's `scripts/` and run it in
`make check`; the python-rules skill's `references/config.md` has the `pyproject.toml` and
`Makefile` fragments, including the import-linter contract for the module order.

The `adk-docs` MCP server starts with the plugin. The docs describe the latest ADK, so the
installed package stays the final check (P5).

## Maintaining the plugin

These rules are for whoever edits the skills, so they live here and not in the skills.

- `charter/SKILL.md` stays within 160 lines (it carries two contracts where adk-bricks had one). Adding a rule means showing what went wrong
  without it (P4).
- IDs keep their meaning. A retired rule keeps its number with a note. `M` rules are the
  module contract, `B` the brick contract, `P` the principles; the python-rules skill numbers
  its sections, not its rules.
- A recipe is written from something that ran. What no sample has proven is named in the
  recipe's last paragraph and stays there until it is.
- When a rule changes, change `check_modules.py` and its tests in the same step; run
  `python3 -m pytest plugins/adk-modules/skills/charter/scripts` from the marketplace root.
- The two skills do not repeat each other: a rule about Python goes in `python-rules`, a rule
  about where code belongs or what crosses an edge goes in the charter. Where the two meet,
  the charter wins and the python-rules profile records the exemption.
