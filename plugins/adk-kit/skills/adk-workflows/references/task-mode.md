# Task delegation: mode='task' / 'single_turn' (ADK 2.x)

| Mode | Parent reaches it via | User interaction | Finishes by |
|---|---|---|---|
| `chat` | `transfer_to_agent` | full conversation | transferring back |
| `task` | a tool named after the sub-agent | may ask the user | calling `finish_task` |
| `single_turn` | a tool named after the sub-agent | none | calling `finish_task` |

Unset mode = `chat` as a sub-agent, `single_turn` as a workflow node.

```python
worker = Agent(
    name='investigator',                 # becomes the tool name
    mode='task',
    description='...',                   # the whole tool description the parent sees
    input_schema=CaseInput,              # delegation tool params (default {'request': str})
    output_schema=CaseFindings,          # finish_task params (default {'result': str})
    instruction='... then call finish_task.',
    tools=[...])
root_agent = Agent(name='coordinator', model=MODEL, sub_agents=[worker],
                   instruction='Call one delegation tool at a time.')
```

- Only the coordinator needs `model=`; sub-agents inherit from the nearest
  `LlmAgent` ancestor.
- `finish_task` is attached automatically; schema violations are returned to
  the model to retry.
- Delegation tools defer their response and must not be called in parallel —
  don't prompt for several delegations in one turn.
- Official rules: don't set `mode` on the root agent; task agents must be
  leaf agents (no sub-agents). Single-turn agents may run in parallel; task
  agents may not. Each runs on its own isolated session branch.
- adk.dev's collaboration page says task mode is disabled for Python graph
  workflow nodes in v2.0.0; on 2.11 the repo sample
  `workflows/agent_in_workflow` (task node, multi-turn) replays green. Pin
  the version and keep a test.
- `RemoteA2aAgent` supports task mode natively since 2.8.
- Prefer task mode over `AgentTool` for typed hand-offs; `AgentTool` remains
  for wrapping an agent whose free-text answer is the tool result.
