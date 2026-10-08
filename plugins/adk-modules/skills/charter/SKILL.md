---
name: charter
description: How to build software on Google ADK 2.x as modules of bricks - a repository cut into domain modules named in the business's language (exposure, investigation, breaches/limit_overdraft), each holding small bricks by kind (models, ports, calculators, tools, agents, workflows, surfaces, callbacks, skills, MCP servers) and composed into apps. It gives the working procedure, the module contract (M1-M5), the brick contract (B1-B9), the strict/free trust levels, the repository shape and a recipe per kind. Use this when a repository's AGENTS.md or CLAUDE.md names the adk-modules charter or the repository has a modules/ folder, and the task is to add or change a module or any kind of brick, to decide which module code belongs to or what may import what, to make an agent's numbers trustworthy or leave it exploratory, to try an idea in spikes/, or when a plan or review cites P1-P6, M1-M5 or B1-B9. For the ADK API use the google-agents-cli-adk-code skill and the adk-docs MCP server as references and the installed package as the final check; the agents-cli command is not used.
---

# Building with modules and bricks

A repository is cut into **modules**, one per area of the domain, named as the business names
it. A module holds **bricks**: small tools, agents, workflows, skills, MCP servers and plain
Python components, grouped by kind. An **app** is an output built from bricks, such as a
container image, and nothing more. The rules cover only what crosses a module's or a brick's
edge; inside you are free.

## How to work here

1. **Name the module** the task belongs to, in the domain's words. Extend it while its
   `__init__.py` docstring still describes the work; otherwise propose a new module and stop,
   because a new module is a person's decision (P6).
2. **Name the kinds** of brick the task touches, from the table below. Extend a brick while the
   opening of its docstring still describes it; otherwise make a new one.
3. **Ask before deciding what the request leaves open about a number:** how it is rounded, its
   unit, what is counted. Those are a person's decisions (P6). If you cannot ask, do what does
   not depend on the answer and report the questions.
4. **Open the recipe of each kind you touch,** and no others, and follow its shape.
5. **Create `modules/<module>/<kind>/<name>/`** (or the same shape inside its only user, B8).
   Its `__init__.py` opens with a docstring saying what the brick is and re-exports it with
   `__all__` (B9): `"""Tool brick, strict. In: an order id from the model. Out: the order's exact total."""`
6. **Export what other modules need** from the module's `__init__.py`, and nothing else (M2).
7. **Write the offline test beside the code** (`test_<name>.py`). For an agent, add an eval
   case when its prompt or tools changed.
8. **Format, run the checks and say which ran:** `uv run ruff format .`, `uv run ruff check .`,
   `uv run pytest`, `uv run python scripts/check_modules.py`. Evals call the real model and
   cost money; run them only when a prompt, a tool's docstring or the model changed, and say
   so when no key is available.
9. **If the request conflicts with a rule below, say so and stop.** Do not work around it;
   changing a rule is a person's decision.

An untried idea goes to `spikes/` first, where none of this applies.

## Principles

- **P1 Small bricks, composed.** A brick does one thing and is small enough to rewrite in a sitting.
- **P2 Strict at the edges, free inside.** Only the contracts below are fixed.
- **P3 Trust is declared.** Some bricks must never invent a number; others exist to explore.
- **P4 Experience before rules.** Try it in `spikes/` first. Propose a rule or an abstraction
  only after something ran and went wrong without it.
- **P5 Do not repeat Google.** The ADK API comes from the `google-agents-cli-adk-code` skill,
  the `adk-docs` MCP server (adk.dev) and the installed `google-adk` package, which is the final
  check and is never replaced by memory. The `agents-cli` command is not used: where Google's
  skill says to run it, use `adk` and `uv` instead.
- **P6 Tools check, people decide.** Types, lint, tests and the check script are checked by
  tools. What needs judgement is decided by a person.

## The module contract

- **M1 One domain, one module.** `modules/<name>/` is an area of the domain, named as the
  business names it. Its `__init__.py` opens with a docstring saying what the area is. A module
  is never named `common`, `shared`, `core` or `utils`: if the domain concept cannot be named,
  it is not a module yet.
- **M2 Public is exported.** A module's `__init__.py` re-exports, with `__all__`, exactly what
  other modules and apps may use. Another module imports from `modules.<name>` and never from a
  path inside it. What is not exported is private to the module.
- **M3 Declared order.** Modules import downward along an order declared once, in
  `pyproject.toml` (`[tool.adk_modules] order`, [module recipe](references/module.md)); modules
  at the same level do not import each other. A new module is added to the order when it is
  created. The order is enforced by the check script and import-linter, not by memory.
- **M4 Bricks inside, by kind.** A module holds its bricks in kind folders (table below). The
  brick contract applies to every brick wherever its module sits. Inside a module, kinds
  import inward: a model imports no other kind, a calculator imports models, a port imports
  models, a tool imports ports and calculators, an agent or workflow imports any kind.
- **M5 A group holds modules and nothing else.** A folder of sibling modules (`breaches/`)
  groups them under one name; its `__init__.py` is a docstring and exports nothing. Siblings
  in a group import each other only if the order says so.

## The brick contract

- **B1 One purpose.** One folder, one purpose. The docstring opens by stating the kind, the
  trust level, what goes in and what comes out. Only a brick without a model may leave the
  trust level out.
- **B2 Typed edge.** Bricks exchange Pydantic models or primitives. What a tool returns to a
  model is a dict of primitives. Money and quantities are `Decimal`, or decimal strings in
  such a dict, with an explicit unit; never `float`.
- **B3 Public interface only.** Inside a module, import another brick from its package
  (`from modules.orders.calc.order_total import order_total`), never from a file inside it.
  Across modules, import only what the module exports (M2). Relative imports stay inside one
  brick (`from .builder import ...`, `from .agents.analyst import ...` for a part).
- **B4 Dependencies are passed in.** The model, settings, clients, the clock and data access
  arrive as arguments, data access as a `Protocol`. A brick reads no environment variable and
  calls no `date.today()`.
- **B5 One offline test.** Every brick has a test beside it that runs without network or a live
  model, using fakes for its `Protocol`s and a scripted model for an agent.
- **B6 Declared trust.** A brick with a model in it is `strict`, `free` or `mixed` (below).
- **B7 Only an entry point touches the outside world.** Reading the environment and choosing
  the real model and data happen in `agent.py`, `__main__.py` or an app, never in the brick.
- **B8 Parts are private.** A brick may hold bricks in the same `<kind>/<name>/` shape inside
  its own folder, at any depth. Only the owner and its other parts import a part, never through
  a re-export. A part needed outside moves up to the nearest brick or module holding all its
  users.
- **B9 Thin `__init__.py`.** A brick's `__init__.py` holds its docstring, imports and
  `__all__`, nothing that computes. The implementation lives in files named by what they
  contain (`order_total.py`, `builder.py`, `port.py`, `fake.py`), private helpers in
  `_<name>.py`. `agent.py` and `__main__.py` are entry points and keep their names.

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

| Kind | Folder in a module | Use it when | Its edge |
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
modules/<module>/<kind>/<name>/   one folder per brick: __init__.py, its test, its recipe's files
modules/<module>/__init__.py      the module's docstring and exports (M1, M2)
modules/<group>/<module>/         sibling modules under one name (M5)
apps/<name>/                      outputs built from bricks; apps/README.md lists them
spikes/                           experiments
scripts/check_modules.py          M1–M5, B3, B5, B8, B9, spikes; run in `make check`
```

- **An agent or workflow brick has three faces.** `build_<name>(model, <ports>)` is the brick,
  for composing and for tests; it assembles its own tools, so they are listed in one place.
  `agent.py` exposes `root_agent` with default wiring, so `adk web`, `adk run` and
  `adk api_server` run it alone. An agent also offers `get_agent_async` for `adk eval`, and
  keeps its eval set in `evals/`.
- **An [app](references/app.md) is not a brick and holds no logic.** Its server names the
  exported agent and workflow bricks it serves, by module, and the routes its frontend calls,
  and serves nothing else; a new brick is added there.
- **`spikes/` is outside these rules.** Nothing outside it imports from it. An experiment worth
  keeping is rebuilt as a brick, not moved in.

The brick recipes were proven in the repository `github.com/kolnago/bricks-v1` (private) on
`google-adk` 2.11.0. Not proven yet, so treat as new ground: the module level itself (M1–M5,
B9, the check script) in a full project, a surface whose layout a model writes, user actions
sent back from a surface, and a Cloud Run deployment.
