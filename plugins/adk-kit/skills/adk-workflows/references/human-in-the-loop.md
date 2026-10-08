# Human in the loop (ADK 2.x)

Three mechanisms:

| Mechanism | Where | Client sees | Client answers |
|---|---|---|---|
| `RequestInput` | any workflow node | function call `adk_request_input` | `FunctionResponse(id=<call id>, name='adk_request_input', response=...)` |
| Tool confirmation | `FunctionTool(require_confirmation=True)` or `tool_context.request_confirmation(hint=...)` | function call `adk_request_confirmation` | `FunctionResponse(..., name='adk_request_confirmation', response={'confirmed': True})` |
| Long-running tool | `LongRunningFunctionTool(func=f)` | the tool's function call, marked long-running | a `FunctionResponse` for that call id |

Since 2.11 tool nodes inside workflows pause for confirmation via
`RequestInput` too.

## RequestInput

```python
yield RequestInput(
    interrupt_id='manager_approval',   # auto UUID if omitted; vary per loop iteration
    message='Please review this request.',
    payload=request,                    # any data shown to the client
    response_schema=Decision,           # Pydantic class, type, or JSON schema dict
)
```

A plain function may `return RequestInput(...)` without becoming a generator.

## rerun_on_resume

- `False` (default for FunctionNode): the node is not re-run; the user's answer
  becomes the node's output and flows downstream.
- `True` (default for LlmAgent nodes, Workflow, parallel workers): the node
  runs again from the top with answers in `ctx.resume_inputs[interrupt_id]`.

Multi-question node:

```python
@node(rerun_on_resume=True)
async def form(ctx: Context, node_input: str):
  if 'ask_name' not in ctx.resume_inputs:
    yield RequestInput(interrupt_id='ask_name', message='Name?'); return
  if 'ask_email' not in ctx.resume_inputs:
    yield RequestInput(interrupt_id='ask_email', message='Email?'); return
  yield Event(output={'name': ctx.resume_inputs['ask_name'],
                      'email': ctx.resume_inputs['ask_email']})
```

**Invalid answers are fatal for that interrupt.** ADK validates the answer
against `response_schema` (coercing e.g. `'500'` → `500`); a failing answer
raises `WorkflowDataError` out of `run_async`, and the invalid response stays
in the session, so even a later valid answer to the same `interrupt_id` fails.
Validate in your API/BFF before calling the runner (verified 2.11). The
function call `id` equals the `interrupt_id`.

Answers with absent schema keys can arrive as `None` — make optional fields
`str | None = None`. Non-dict answers arrive under `{'result': ...}`.

## Resumable vs replay

- No `App` / `is_resumable=False`: each answer replays from `START`; completed
  nodes are skipped and state is rebuilt from events. Fine for one interrupt.
- `App(..., resumability_config=ResumabilityConfig(is_resumable=True))`:
  checkpoints into `event.actions.agent_state` and resumes at the paused node.
  Use for loops, long-running tools, large graphs, node-as-tool HITL.
  Emits an EXPERIMENTAL warning in 2.11.
- A restart loses the pause unless sessions are durable (`adk-app-runtime`,
  default 4, has the stores and URIs).

## Client loop

```python
fc = next(c for e in events for c in e.get_function_calls()
          if c.name == 'adk_request_input')
resume = types.Content(role='user', parts=[types.Part(
    function_response=types.FunctionResponse(
        id=fc.id, name=fc.name, response={'approved': True}))])
async for ev in runner.run_async(user_id=u, session_id=s, new_message=resume):
  ...
```
