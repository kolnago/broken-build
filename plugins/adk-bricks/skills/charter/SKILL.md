---
name: charter
description: How to build software as bricks on Google ADK 2.x - small tools, agents, workflows, skills, MCP servers, A2UI surfaces and Python components (models, ports, calculators) under bricks/, composed into apps. It gives the working procedure, the eight-rule brick contract (B1-B8), the strict/free trust levels, which folder each kind lives in and a recipe per kind. Use this when a repository's AGENTS.md or CLAUDE.md names the adk-bricks charter or the repository has a bricks/ folder, and the task is to add or change a tool, agent, workflow, skill, MCP server, surface, callback, calculator, port, model or app, to decide where code belongs or what may import what, to make an agent's numbers trustworthy or leave it exploratory, to try an idea in spikes/, or when a plan or review cites P1-P6 or B1-B8. For the ADK API itself use the google-agents-cli-adk-code skill as a reference and the installed package; the agents-cli command is not used.
---

# Building with bricks

Software here is composed from small bricks: tools, agents, workflows, skills, MCP servers and
plain Python components. The rules cover only what crosses a brick's edge; inside a brick you
are free. An app is an output built from bricks, such as a container image, and nothing more.

## How to work here

1. **Name the kinds** of brick the task touches, from the table below. Extend an existing
   brick while the opening of its docstring still describes it; otherwise make a new one.
2. **Ask before deciding what the request leaves open about a number:** how it is rounded,
   its unit, what is counted. Those are a person's decisions (P6). If you cannot ask, do
   what does not depend on the answer and report the questions.
3. **Open the recipe of each kind you touch,** and no others, and follow its shape.
4. **Create `bricks/<folder>/<name>/`** (or the same shape inside its only user, B8). Its
   `__init__.py` opens with a docstring saying what the brick is, and exports it with `__all__`:
   `"""Tool brick, strict. In: an order id from the model. Out: the order's exact total."""`
5. **Write the offline test beside the code** (`test_<name>.py`). For an agent, add an eval
   case when its prompt or tools changed.
6. **Format, run the checks and say which ran:** `uv run ruff format .`, `uv run ruff check .`,
   `uv run pytest`. Evals call the real model and cost money; run them only when a prompt, a
   tool's docstring or the model changed, and say so when no key is available.
7. **If the request conflicts with a rule below, say so and stop.** Do not work around it;
   changing a rule is a person's decision.

An untried idea goes to `spikes/` first, where none of this applies.

## Principles

- **P1 Small bricks, composed.** A brick does one thing and is small enough to rewrite in a sitting.
- **P2 Strict at the edges, free inside.** Only the contract below is fixed.
- **P3 Trust is declared.** Some bricks must never invent a number; others exist to explore.
- **P4 Experience before rules.** Try it in `spikes/` first. Propose a rule or an abstraction
  only after something ran and went wrong without it.
- **P5 Do not repeat Google.** The ADK API comes from the `google-agents-cli-adk-code` skill as
  a reference, the adk.dev docs, and the installed `google-adk` package, which is the final
  check and is never replaced by memory. The `agents-cli` command is not used: where Google's
  skill says to run it, use `adk` and `uv` instead.
- **P6 Tools check, people decide.** Types, lint and tests are checked by tools. What needs
  judgement is decided by a person.

## The brick contract

- **B1 One purpose.** One folder, one purpose. The docstring opens by stating the kind,
  the trust level, what goes in and what comes out. Only a brick without a model may leave
  the trust level out.
- **B2 Typed edge.** Bricks exchange Pydantic models or primitives. What a tool returns to a
  model is a dict of primitives. Money and quantities are `Decimal`, or decimal strings in
  such a dict, with an explicit unit; never `float`.
- **B3 Public interface only.** Import another brick from its package (`bricks.calc.order_total`),
  never from a module inside it.
- **B4 Dependencies are passed in.** The model, settings, clients, the clock and data access
  arrive as arguments, data access as a `Protocol`. A brick reads no environment variable and
  calls no `date.today()`.
- **B5 One offline test.** Every brick has a test that runs without network or a live model,
  using fakes for its `Protocol`s and a scripted model for an agent.
- **B6 Declared trust.** A brick with a model in it is `strict`, `free` or `mixed` (below).
- **B7 Only an entry point touches the outside world.** Reading the environment and choosing
  the real model and data happen in `agent.py`, `__main__.py` or an app, never in the brick.
- **B8 Parts are private.** A brick may hold bricks in the same `<folder>/<name>/` shape inside
  its own folder, at any depth. Only the owner and its other parts import a part, never through
  a re-export. A part needed outside moves up to the nearest brick holding all its users.

## Trust

- **`strict`**: every number in the output was produced by code. A brick without a model is
  strict by construction. An agent is strict when it attaches the number guard, which blocks
  a reply containing a number no tool produced ([callback recipe](references/callback.md)).
- **`free`**: the brick may reason, estimate and explore. It attaches the label callback, so
  its replies are marked unverified wherever a person sees them.
- **`mixed`**: an agent made of strict and free agents. Each part keeps its own level.
- **Crossing the line.** A strict brick treats a free brick's output as untrusted input, like
  text typed by a user: it may read it and never repeats a number from it as fact. A strict
  agent that uses a free agent as a tool names it as untrusted in the guard.

## Kinds of brick

| Kind | Folder | Use it when | Its edge |
|---|---|---|---|
| [Model](references/model.md) | `models/` | bricks share a value, such as money | the Pydantic class |
| [Port, adapter, fake](references/port.md) | `ports/` | code needs data or a system outside | the `Protocol` |
| [Calculator](references/calculator.md) | `calc/` | anything is added, multiplied, compared or rounded | typed arguments in, typed result out |
| [Tool](references/tool.md) | `tools/` | a model must fetch or do something | primitive parameters, a docstring for the model, a dict out |
| [Surface](references/surface.md) | `surfaces/` | the user should see UI, not prose | a list of A2UI messages; amounts as formatted strings |
| [Callback](references/callback.md) | `callbacks/` | behaviour applies around any agent, such as a guard | the hooks it implements |
| [Agent](references/agent.md) | `agents/` | the task needs judgement or language | the question it accepts and its answer, with its trust level |
| [Workflow](references/workflow.md) | `workflows/` | the steps are fixed and you could draw them | first node's input, last node's output |
| [Skill](references/skill.md) | `skills/` | an agent needs instructions only sometimes | its name and description |
| [MCP server](references/mcp-server.md) | `mcp/` | other clients need the same tools | the tool schemas it serves |
| [Scripted model](references/scripted-model.md) | `fakes/` | an agent test needs a model | the replies it is given |

If you can write the decision as code, use a calculator or a workflow, not an agent. Bricks
compose into bigger bricks: an agent made of agents is still one agent brick, parts inside (B8).

## Repository shape

```
bricks/<folder>/<name>/   one folder per brick: __init__.py, its test, its recipe's other files
  <folder>/<name>/        a part: a brick only its owner and the owner's parts use (B8)
apps/<name>/              outputs built from bricks; apps/README.md lists them
spikes/                   experiments
```

- **An agent or workflow brick has three faces.** `build_<name>(model, <ports>)` is the brick,
  for composing and for tests; it assembles its own tools, so they are listed in one place. `agent.py` exposes `root_agent` with default wiring, so `adk web`,
  `adk run` and `adk api_server` run it alone. An agent also offers `get_agent_async` for
  `adk eval`, and keeps its eval set in `evals/`.
- **An [app](references/app.md) is not a brick and holds no logic.** Its server names top-level
  bricks and the routes its frontend calls, and serves nothing else; a new brick is added there.
- **`spikes/` is outside these rules.** Nothing outside it imports from it. An experiment worth
  keeping is rebuilt as a brick, not moved in.

A complete example of this shape is the repository `github.com/kolnago/bricks-v1` (private).
Not proven there yet, so treat as new ground: a surface whose layout a model writes, user
actions sent back from a surface, and a Cloud Run deployment.
