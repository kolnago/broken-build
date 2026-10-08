# ADK architecture guide v2.0 — §8 Tools, the turn ledger, the derive tool, the Pattern A shell, MCP exposure

Part of the guide split by section. Rule summary and file index: [../SKILL.md](../SKILL.md); overview, principles and layers: [overview.md](overview.md).

---

## 8. Tools and the analyst agent

### 8.1 What the agent is for

The agent's instructions should give it real work: decide which tools answer the user's question, call several when the question needs it, connect findings, rank what matters, and write for the reader. Instructions that reduce it to "call tool X and repeat the output" mean the design should be a fixed workflow instead (Pattern B).

- **AGT-1** The agent has access to a **curated toolset** of question-shaped tools (`CORE-17`) plus `derive`. It never has raw table or SQL tools (`TOOL-7`).
- **AGT-2** Instructions state the rule once, plainly: *"Numbers come only from tool results. If you need a number no tool returned, call `derive`. Never compute, estimate, or round yourself."*
- **AGT-3** Instructions describe the reader and the expected shape of an answer (finding → evidence → recommendation), not a rigid template.
- **AGT-4** The agent may quote a figure's `display` exactly or a rounded form of it (§9.2); it may not combine figures in prose.
- **AGT-5** Prompts live in `agents/<name>/prompts/*.md`, versioned with code.

### 8.2 Tool rules

- **TOOL-1** Tools are thin adapters in `tools/`: convert primitive arguments, call a service, return a JSON-safe `dict` with `status`.
- **TOOL-2** The docstring is the tool's prompt: what it answers, when to use it, parameters, return shape, and that figures are final. Do not document the injected context parameter.
- **TOOL-3** Numeric results are returned **only as figure views**: `figure_id`, `label`, `display`, `value` (as string), `unit`. Never raw rows, never bare floats.
- **TOOL-4** Parameters are primitives (`str`, `int`, `Literal`); dates as ISO strings parsed in code.
- **TOOL-5** Every tool that returns figures **records them in the turn ledger** (§8.3) before returning.
- **TOOL-6** Expected domain errors return `{"status": "error", "message": ...}`; unexpected errors propagate.
- **TOOL-7** No generic SQL-execution or raw-table tools in production agents.
- **TOOL-8** Session context (identity, scope, default as-of) is read only in the adapter and passed to services explicitly.
- **TOOL-9** Results are compact. Cap lists; return "top N plus count" rather than everything.

```python
# tools/limit_tools.py
import asyncio
from google.adk.tools import ToolContext          # verified: google-adk 2.11.0 (ToolContext is Context)
from app.core.errors import AmbiguousReference, DataNotAvailable, EntityNotFound
from app.core.models.requests import EntitlementScope
from app.core.services.limits import LimitService
from app.tools.ledger import figure_views, record
from app.workflows.shell import keys

def build_limit_tools(svc: LimitService) -> list:
    async def get_limit_utilization(portfolio_ref: str, as_of: str, tool_context: ToolContext) -> dict:
        """Limit utilisation for one portfolio on a business date.

        Use when the user asks how close a portfolio is to its limit, whether it is breached,
        or how much headroom remains. Returns exposure, limit, utilisation ratio, headroom,
        and the flags `breached` and `near_limit`.

        Args:
            portfolio_ref: Portfolio ID or name as the user wrote it.
            as_of: Business date, YYYY-MM-DD.

        Returns:
            {"status": "ok", "figures": [{"figure_id", "label", "display", "value", "unit"}, ...]}
            or {"status": "error", "message": str}.
            Figures are final. To combine two figures, call `derive`.
        """
        scope = EntitlementScope.model_validate(tool_context.state[keys.SCOPE])
        try:
            req = await asyncio.to_thread(svc.resolve, portfolio_ref, as_of, scope)
            fs = await asyncio.to_thread(svc.utilization, req)
        except (EntityNotFound, AmbiguousReference, DataNotAvailable) as e:
            return {"status": "error", "message": e.user_message}
        record(tool_context, fs.figures)                       # TOOL-5
        return {"status": "ok", "as_of": fs.as_of.isoformat(), "figures": figure_views(fs.figures)}

    return [get_limit_utilization]
```

### 8.3 The turn ledger

The ledger is the set of figures returned by tools during the current invocation. It is what the verifier trusts.

- **LED-1** The ledger lives in session state under a `temp:` key so it is discarded after the invocation.
- **LED-2** Only tools write to it, only via `tools/ledger.py`. The model cannot add entries.
- **LED-3** Entries are full `Figure`s (JSON-dumped), so the verifier has exact values, displays, and units.

```python
# tools/ledger.py
from app.core.models.figures import Figure
from app.workflows.shell import keys

def record(tool_context, figures: tuple[Figure, ...]) -> None:
    ledger = dict(tool_context.state.get(keys.LEDGER, {}))
    for f in figures:
        ledger[f.figure_id] = f.model_dump(mode="json")
    tool_context.state[keys.LEDGER] = ledger                     # verified: google-adk 2.11.0 (records a delta)

def figure_views(figures: tuple[Figure, ...]) -> list[dict]:
    return [{"figure_id": f.figure_id, "label": f.label, "display": f.display,
             "value": str(f.value), "unit": f.unit} for f in figures]

def read(state) -> dict[str, Figure]:
    return {k: Figure.model_validate(v) for k, v in state.get(keys.LEDGER, {}).items()}
```

### 8.4 The derive tool

- **DRV-1** `derive(operation, figure_ids)` applies one operation from `core/calc/derive.py` to figures already in the ledger, records the result, and returns it as a figure view.
- **DRV-2** It refuses unknown operations, unknown figure IDs, and unit mismatches with a clear error the model can act on.

```python
# tools/derive.py
from typing import Literal
from app.core.calc import derive as ops
from app.tools.ledger import figure_views, read, record

Operation = Literal["difference", "ratio", "pct_change", "sum", "max", "min"]

def build_derive_tool() -> list:
    def derive(operation: Operation, figure_ids: list[str], tool_context) -> dict:
        """Compute a new figure from figures returned earlier in this conversation turn.

        Use instead of doing arithmetic yourself. Operations: difference(a, b), ratio(a, b),
        pct_change(new, old), sum(...), max(...), min(...). Inputs must share a unit.

        Args:
            operation: One of the listed operations.
            figure_ids: figure_id values from earlier tool results, in argument order.

        Returns:
            {"status": "ok", "figures": [figure]} or {"status": "error", "message": str}.
        """
        ledger = read(tool_context.state)
        missing = [i for i in figure_ids if i not in ledger]
        if missing:
            return {"status": "error", "message": f"Unknown figure ids: {missing}. Fetch them with a tool first."}
        try:
            result = getattr(ops, operation)(*(ledger[i] for i in figure_ids))
        except (ops.UnitMismatch, ZeroDivisionError, TypeError) as e:
            return {"status": "error", "message": str(e)}
        record(tool_context, (result,))
        return {"status": "ok", "figures": figure_views((result,))}
    return [derive]
```

### 8.5 Pattern A shell workflow

```python
# workflows/shell/graph.py
from google.adk import Agent, Context, Event, Workflow     # verified: google-adk 2.11.0
from google.adk.workflow import START
from app.config import Settings
from app.core.guardrails.numbers import verify_numbers
from app.core.models.requests import EntitlementScope
from app.tools.ledger import read
from app.workflows.shell import keys, routes
from app.workflows.shell.fallback import figures_only

def build_shell(agent: Agent, settings: Settings) -> Workflow:

    def prepare(ctx: Context, node_input: str):
        EntitlementScope.model_validate(ctx.state[keys.SCOPE])   # SH-1; raises out of run_async: catch in api/
        return Event(output=node_input, state={keys.LEDGER: {}, keys.ATTEMPTS: 0, keys.USER_TEXT: node_input})

    def verify(ctx: Context, node_input: str):
        answer = node_input                                       # str: the agent has no output_schema
        report = verify_numbers(answer, read(ctx.state), user_text=ctx.state[keys.USER_TEXT])
        if report.ok:
            return Event(output=answer, route=routes.PASS)        # routed events must carry output
        attempts = ctx.state.get(keys.ATTEMPTS, 0)
        if attempts < settings.verify_max_retries:
            retry_input = (f"Question: {ctx.state[keys.USER_TEXT]}\n\n"   # SH-2: the agent sees only this
                           "Your previous answer contained numbers not returned by any tool: "
                           + "; ".join(report.violations)
                           + ". Call the tools again if needed and answer using only tool figures, or call derive.")
            return Event(output=retry_input, route=routes.RETRY, state={keys.ATTEMPTS: attempts + 1})
        return Event(output=figures_only(read(ctx.state)), route=routes.FAIL)

    def deliver(node_input: str):                                 # terminal node (ADK has no END sentinel)
        yield Event(message=node_input)
        yield Event(output=node_input)

    def fallback(node_input: str):                                # terminal node, SH-3
        yield Event(message=node_input)
        yield Event(output=node_input)

    return Workflow(
        name="analyst_shell",
        edges=[
            (START, prepare, agent, verify),
            (verify, {routes.PASS: deliver, routes.RETRY: agent, routes.FAIL: fallback}),  # routed cycle: legal
        ],
    )
```

The agent node inside the graph keeps its tools; ADK 2.0 agents in a graph run in `single_turn` or `task` mode. Multi-turn conversation is handled by the runner calling the workflow once per user message with the session preserved; the ledger is `temp:` and resets each turn while the conversation history does not.

- **SH-1** `prepare` fails fast if identity or scope is missing. It never defaults them.
- **SH-2** On retry, the agent node runs with only the retry input. A `single_turn` agent re-entered by a loop does not see the original message or earlier tool results, so the verifier's retry input restates the question (`keys.USER_TEXT`) with the feedback. The ledger keeps this turn's figures across the retry.
- **SH-3** After the retry budget is spent, the fallback shows the ledger figures without narrative. An unverified answer is never delivered.
- **SH-4** Alternative placement: an `after_model_callback` on the agent can run the same `verify_numbers`. Prefer the graph node; it is visible, testable, and gives a clean retry route. `# VERIFY` callback semantics in 2.x before choosing it.

### 8.6 MCP exposure

Because services are framework-free, an MCP server can expose the same tools without touching agents or core. Add it when a second consumer appears (other agents, IDE assistants, other teams), when security requires the agent runtime to hold no data credentials, or when the calculation engine needs its own release cycle. Deploy it as a **separate service** with its own service account; in-process MCP adds overhead without isolation.
