# Orchestration patterns (ADK 2.x)

| You need | Use | Replaces |
|---|---|---|
| Sequence | `(START, a, b, c)` | `SequentialAgent` |
| Branch | `(classify, {'x': a, 'y': b, DEFAULT_ROUTE: c})` | custom agent |
| Loop | routed back-edge / self-edge | `LoopAgent` |
| Parallel, different work | `(START, (a, b, c))` + `((a, b, c), JoinNode(name='j'))` | `ParallelAgent` |
| Parallel, same work per item | `@node(parallel_worker=True, max_parallel_workers=N)` | — |
| Python control flow | `await ctx.run_node(...)` | custom `BaseAgent` |
| Reuse | nest a `Workflow` as a node / pass it in `tools` | — |

## Edge syntax

```python
edges = [
    (START, a),                         # simple
    (START, a, b, c),                   # chain
    (a, b, 'route'),                    # routed (one target)
    (a, b, ['r1', 'r2']),               # routed (any of several)
    (a, {'ok': b, 'err': c}),           # route map
    (a, (b, c)),                        # fan-out
    ((b, c), join),                     # fan-in
]
```

Routes may be `str`, `bool`, `int`, or a list (fires several branches).
`DEFAULT_ROUTE` (`'__DEFAULT__'`) fires when no other route matches and may not
be mixed into a list. Two edges with the same source and target are rejected
even with different routes — use a thin wrapper node.

## Loops into LLM agents (verified 2.11)

A loop-back into an agent node in `single_turn` mode (the default in graphs)
runs it with only the new `node_input`: no original user message, no earlier
tool calls. For a verify→retry loop, make the feedback node emit the question
and the feedback together, or keep the question in state and reference it in
the instruction (`{temp:user_text?}`). `temp:` keys written by tools inside
the agent are readable by later nodes in the same invocation and are not
persisted.

Routed events must carry `output=` when the target needs input; a
message-only routed event delivers `None`. There is no `END` node — terminals
are nodes without outgoing edges.

## Fan-out vs multi-trigger vs join

- Fan-out into three nodes then **one shared successor without a join** → the
  successor runs three times (once per branch).
- With a `JoinNode` → runs once with `{'a': ..., 'b': ..., 'c': ...}`.
- `JoinNode` parks partial inputs in session state → they must be
  JSON-serialisable (`output_schema` on LLM predecessors).
- Never put `parallel_worker=True` on a fan-out branch (it then expects a list;
  `None` input emits nothing and the join waits forever).

## Parallel worker facts

Non-list input is wrapped in a one-item list; empty list → empty list and
downstream still fires; `rerun_on_resume` forced True; `max_parallel_workers`
≥ 1. On an `LlmAgent` set `parallel_worker=True` on the agent.

## Dynamic nodes

```python
@node(rerun_on_resume=True)
async def orchestrate(ctx: Context, node_input: str):
  a = await ctx.run_node(step_a, node_input=node_input)
  if 'ok' in a:
    yield Event(output=await ctx.run_node(step_b, node_input=a))
  else:
    yield Event(output=await ctx.run_node(step_c, node_input=a))
```

- Raw functions passed to `run_node` receive the value only through a parameter
  literally named `node_input` (others bind from state).
- A child that itself calls `run_node` also needs `rerun_on_resume=True`
  (wrap: `FunctionNode(func=f, rerun_on_resume=True)`).
- `use_as_output=True` at most once per parent run.
- Do not wrap in `asyncio.create_task` — errors are swallowed and cancellation
  is lost.

## Nested workflows

```python
inner = Workflow(name='inner', edges=[(START, a, b)])
outer = Workflow(name='outer', edges=[(START, pre, inner, post)])
```

## Retries, timeouts, cancellation

```python
@node(retry_config=RetryConfig(max_attempts=3, initial_delay=1.0, exceptions=[ConnectionError]),
      timeout=30.0)
def call_api(ctx: Context, node_input: str) -> str: ...
```

`RetryConfig` fields default to None = built-in fallback (5 attempts, 1s
initial, 60s max, ×2 backoff, jitter 1.0). Timeout raises `NodeTimeoutError`
(retried like any error). Retry count is not persisted across resumes.
Cancellation: `runner.run_async(..., abort_signal=asyncio.Event())` →
`INVOCATION_ABORTED` event; check `ctx.is_aborted` in long loops.

## Declarative graphs (2.9+)

YAML with `agent_class: Workflow` and `edges:` mixing `.agent.fn` references
and `other.yaml` agent files; see `contributing/samples/workflows/loop_config`.
