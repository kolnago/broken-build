---
name: adk-workflows
description: Build Google ADK 2.x (google-adk 2.x, verified on 2.11) Python agents and graph workflows - Workflow edges, function and LlmAgent nodes, routing, loops, fan-out/JoinNode, parallel workers, ctx.run_node, RequestInput human-in-the-loop, task/single_turn delegation, node-as-tool, tools and MCP. Use when writing or changing ADK agent code, choosing an orchestration pattern, or migrating SequentialAgent/ParallelAgent/LoopAgent to Workflow. Prefer it over google-agents-cli's adk-code and workflow skills when you need tested code and verified 2.11 gotchas; for layers, figures and number rules use adk-architecture.
---

# ADK 2.x workflows and agents

Target: `google-adk>=2.11`, Python 3.10+. ADK 2.x only — never generate
`SequentialAgent`, `ParallelAgent` or `LoopAgent` for new code; they are
deprecated shells over `Workflow`.

## Before writing code

1. Confirm the installed version: `python -c "import google.adk; print(google.adk.__version__)"`.
   If a symbol below is missing, read the installed package's source
   (`google/adk/` in site-packages, or `src/google/adk/` in an adk-python
   clone) instead of guessing a neighbouring name.
2. Pick the pattern from the table, open only the matching reference, and copy
   from the matching example in `examples/` (all tested offline on 2.11 by the
   `adk-testing` skill's suite).

| Need | Pattern | Example | Reference |
|---|---|---|---|
| Fixed steps | `edges=[(START, a, b, c)]` | `ex01_function_pipeline.py` | `references/nodes-events-context.md` |
| Branch / loop | `Event(route=...)` + `{route: node}` map, `DEFAULT_ROUTE` | `ex02_routing_loop.py` | `references/patterns.md` |
| Parallel then merge | tuple fan-out + `JoinNode`; `@node(parallel_worker=True)` per item | `ex03_fan_out_join.py` | `references/patterns.md` |
| LLM step in a graph | `Agent(..., output_schema=M)` placed in edges | `ex04_llm_agent_nodes.py` | `references/nodes-events-context.md` |
| Human approval | `RequestInput` + `App(resumability_config=...)` | `ex05_human_in_the_loop.py` | `references/human-in-the-loop.md` |
| Control flow in Python | `await ctx.run_node(...)` in `@node(rerun_on_resume=True)` | `ex06_dynamic_nodes.py` | `references/patterns.md` |
| Model delegates typed job | `sub_agents=[Agent(mode='task' or 'single_turn', input_schema, output_schema)]` | `ex07_task_mode.py` | `references/task-mode.md` |
| Workflow callable by a model | pass `Workflow` / `@node` in `tools` | `ex08_node_as_tool.py` | `references/tools.md` |
| Tools, confirmation, MCP | functions, `FunctionTool(require_confirmation=True)`, `McpToolset` | `ex09_tools.py` | `references/tools.md` |
| Plugins, callbacks, retries | `App(plugins=[...])`, `before_model_callback`, `RetryConfig` | `ex10_app_plugins.py` | `adk-app-runtime` skill |

## Canonical imports

```python
from google.adk import Agent, Context, Event, Runner, Workflow   # only these 5 at top level
from google.adk.workflow import START, DEFAULT_ROUTE, JoinNode, RetryConfig, node, FunctionNode, BaseNode
from google.adk.events import RequestInput
from google.adk.apps import App, ResumabilityConfig
from google.adk.tools import FunctionTool, LongRunningFunctionTool, ToolContext, AgentTool
```

`from google.adk import START` fails — `START` lives in `google.adk.workflow`.

## Rules that prevent most broken workflows

The numbers are stable: `adk-app-runtime`, `adk-testing` and the test suite cite them. Add new
rules at the end; never renumber.

1. **Type with Pydantic.** Annotate `node_input` with a `BaseModel`; dicts are
   coerced. Set `output_schema` on any LlmAgent whose output feeds a node that
   needs fields, and always before a `JoinNode`.
2. **`output` is data, `message` is UI.** `Event(output=x)` feeds the next
   node; `Event(message='...')` is what `adk web` renders. Function nodes do not
   show anything unless they yield a message.
3. **One output event per node run.** A second one silently turns the
   downstream input into a list; a second `route` raises.
4. **Yield or return, never both.** In a generator node, produce the result with
   `yield Event(output=...)`; a `return value` is lost.
5. **Write state with `Event(state={...})`** in nodes (replay-safe). In tools and
   callbacks `tool_context.state[k] = v` is fine.
6. **Instruction `{key}` reads state, never `node_input`.** `{key?}` tolerates a
   missing key. The predecessor's output already arrives as the user message.
7. **Every outgoing edge of a routing node carries a route.** An unrouted edge
   fires on every output. A cycle needs at least one routed edge.
8. **`mode='chat'` agents only directly after `START`.** Agents placed in edges
   default to `single_turn`.
9. **Parallel terminals must join.** Several terminal nodes producing output →
   `ValueError` at the end; merge with a `JoinNode`.
10. **`ctx.run_node` needs `rerun_on_resume=True`** on the caller; custom
    `run_id`s need a non-digit; always `await` it directly.
11. **Unique `interrupt_id` per loop iteration** for `RequestInput`, or the loop
    restarts forever.
12. **Idempotent side effects.** Since 2.9 a failed node re-runs on resume.
13. **Everything in output/state must be JSON-serialisable** (Database session
    service raises; in-memory hides it).
14. **Workflow copies agents at construction.** Configure agents (model,
    tools, callbacks) before building the graph.
15. Export both `root_agent` and `app` from `agent.py` (what `App` carries and how the CLI
    loads it: `adk-app-runtime`, default 1).
16. **Validate human answers before resuming.** An answer that fails a
    `RequestInput.response_schema` raises `WorkflowDataError` out of
    `run_async`, and that interrupt keeps failing in the session even for a
    later valid answer (verified 2.11).
17. **Loop-back into a `single_turn` agent loses context.** On the second pass
    the model sees only the new `node_input` — not the original question or
    earlier tool results. Send question + feedback together, or read the
    question from state in the instruction (verified 2.11).
18. **Routed events need `output=` if the target takes input** — a
    message-only routed event hands the successor `None`. There is no `END`
    sentinel: a graph ends at nodes with no outgoing edges (`"END"` as a
    target fails construction).
19. `mode='task'` nodes work in 2.11 workflows (repo sample
    `workflows/agent_in_workflow` replays green) although adk.dev's
    collaboration page says task is disabled in graph workflows in 2.0.0 —
    keep a test. Never set `mode` on the root agent; task agents are leaves.

## Project layout

```text
my_app/
├── __init__.py   # from . import agent
├── agent.py      # root_agent = ...; app = App(name='my_app', root_agent=root_agent, ...)
└── .env          # GOOGLE_GENAI_USE_ENTERPRISE=TRUE, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION
```

In an `adk-architecture` project the layout is the guide's
(`agents/<name>/agent.py` over `core/`, `data/`, `tools/`, `workflows/`); this
one is the bare ADK minimum. Test with the `adk-testing` skill.

Run with `adk web .` (dev UI), `adk run my_app`, `adk api_server .`.
Pin `model=` explicitly: a named version from the project's settings, never
ADK's built-in default (`gemini-3.5-flash` in the 2.11 source, undocumented)
and never a `*-latest` alias as adk.dev examples use. The examples here take
the name from `ADK_MODEL` (`_common.py`) only so the tests can inject a
scripted model; their fallback name is a placeholder.

## Where to read more in an adk-python checkout

- Unit guides: `docs/guides/workflow/*`, `docs/guides/agents/llm_agent/{task,single_turn}.md`,
  `docs/guides/events/request_input`, `docs/guides/tools/node_tool`.
- One-concept samples: `contributing/samples/workflows/*` (all 2.x).
- Deep internals: `.agents/skills/adk-architecture/`.
