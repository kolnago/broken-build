# Nodes, Events and Context (ADK 2.x)

## Function nodes

Any callable in `edges` is wrapped in a `FunctionNode`. Use `@node(...)` or
`FunctionNode(func=..., ...)` only to set options.

| Parameter name | Bound to |
|---|---|
| `ctx` | the node's `Context` |
| `node_input` | predecessor output, coerced to the annotation (Pydantic `TypeAdapter`) |
| anything else | `ctx.state[name]`, else the parameter default |

`@node` keywords: `name`, `rerun_on_resume`, `retry_config`, `timeout`,
`parallel_worker`, `max_parallel_workers`, `auth_config`, `parameter_binding`.

Return values: a plain value becomes `Event(output=value)`; `None` emits
nothing (downstream stays idle); a returned `BaseModel` is `model_dump()`ed.
Generators may yield `Event`s, `RequestInput`s or bare values.

## What `node_input` will be

| Predecessor | `node_input` |
|---|---|
| `START`, no `input_schema` | `types.Content` (annotate `str` to get text) |
| `START` with `input_schema` | parsed schema type |
| function returning X / `Event(output=X)` | X |
| `LlmAgent` without `output_schema` | `str` (text parts, thoughts excluded) |
| `LlmAgent` with `output_schema` | `dict` |
| `JoinNode` | `dict` keyed by predecessor node name |
| `parallel_worker=True` node | `list`, input order |

A union annotation (`list | dict`) accepts anything — check with `isinstance`.

## Event

| Constructor arg | Lands in | Meaning |
|---|---|---|
| `output=` | `event.output` | data for the next node (one per node run) |
| `message=` | `event.content` | UI text / parts; `partial=True` streams |
| `state=` | `event.actions.state_delta` | persisted, replay-safe |
| `route=` | `event.actions.route` | str / bool / int or list of them |

`message` and `content` are mutually exclusive. Identify the emitting node with
`event.node_info.path` (`'wf@1/step@1'`); `event.author` is the enclosing
workflow.

## Context

Same class everywhere (`ToolContext`, `CallbackContext` are aliases).

| Member | Notes |
|---|---|
| `state` | delta-aware; no iteration/`keys()`/`del` — use `to_dict()` |
| `session`, `user_id`, `invocation_id`, `user_content` | read-only facts |
| `resume_inputs` | HITL answers keyed by `interrupt_id` |
| `attempt_count` | 1 on first try |
| `node_path`, `run_id`, `branch` | identity of this node run |
| `is_aborted` | abort_signal set |
| `actions.skip_summarization` | node-as-tool: return output verbatim |
| `await run_node(node, node_input=None, *, use_as_output=False, run_id=None, use_sub_branch=False, override_branch=None)` | dynamic scheduling |
| `await save_artifact(name, part)` / `load_artifact(name)` | versioned bytes |
| `await search_memory(query)` | long-term memory |
| `request_confirmation(hint=...)`, `tool_confirmation` | tool confirmation |

## LlmAgent as a node

- Auto-wrapped with `mode='single_turn'` (if unset), `rerun_on_resume=True`,
  its own content branch.
- `output_schema=M` → downstream gets `dict`; `output_key='k'` stores the
  result in state (a dict, not a model instance).
- `include_contents='none'` → no history at all.
- `instruction` may be a callable `(ReadonlyContext) -> str`.
- `generate_content_config=types.GenerateContentConfig(temperature=...)` for
  model knobs only — tools, system instruction and schema go on agent fields.
- The runner clears `event.output` on the agent's own event before you see it;
  assert on the next node, `state[output_key]` or `event.content`.

## Workflow

Options: `name`, `edges`, `description`, `input_schema`, `output_schema`,
`state_schema`, `max_concurrency`, `timeout`, `retry_config`,
`rerun_on_resume` (default True). Validation at construction: unique names,
`START` present with no incoming edges and no routed outgoing edges, all nodes
reachable, no duplicate source→target pair, no unconditional cycle, matching
schemas across an edge, no edge into a chat-mode agent except from `START`.

Terminal nodes (no outgoing edges) produce the workflow output. More than one
terminal output at the end → `ValueError`.

## Custom BaseNode

```python
class BatchNode(BaseNode):
  batch_size: int = 10          # Pydantic fields

  @override
  async def _run_impl(self, *, ctx, node_input):   # never override run()
    yield Event(output=...)
```

Fields: `name`, `description`, `rerun_on_resume`, `wait_for_output`,
`retry_config`, `timeout`, `input_schema`, `output_schema`, `state_schema`.
