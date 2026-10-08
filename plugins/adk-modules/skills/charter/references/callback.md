# Callback brick

Behaviour applied around an agent's model and tool calls, such as a guardrail or a label.

## Shape

```
modules/verification/callbacks/number_guard/
├── __init__.py              docstring; re-exports the callbacks; __all__
├── number_guard.py          the callbacks
├── _numbers.py              the pure functions they use (numbers_in, invented)
└── test_number_guard.py
```

```python
# number_guard.py
def collect_tool_numbers(tool, args, tool_context, tool_response) -> None:
    seen = set(tool_context.state.get(SEEN_KEY, []))            # SEEN_KEY = "temp:number_guard_seen"
    seen |= {str(n) for n in numbers_in(json.dumps(tool_response, default=str))}
    tool_context.state[SEEN_KEY] = sorted(seen)

def block_invented_numbers(callback_context, llm_response) -> LlmResponse | None:
    ...                                   # return None to leave the reply as it is
```

An agent brick attaches them:
`Agent(..., after_tool_callback=collect_tool_numbers, after_model_callback=block_invented_numbers)`.
When one of its tools is a free agent, it uses `collect_tool_numbers_except("brainstormer")`
instead, which skips the named tools' results.

The callbacks live in the module that owns trust, and that module exports them (M2), so every
agent in every module attaches the same guard.

## Test

Keep the decision in pure functions (`numbers_in`, `invented`) and test those without ADK.
The callbacks themselves are exercised by the agent brick's test.

## Traps

- **ADK calls callbacks by keyword.** The parameter names must be exactly
  `callback_context, llm_response` and `tool, args, tool_context, tool_response`
  (checked on `google-adk` 2.11.0). ADK fixes the signature, so the python-rules keyword-only
  rule does not apply to a callback (its profile records this).
- **Return `None` to change nothing.** Skip replies that are partial or carry no text; a
  reply that only calls a tool has no text.
- **A `temp:` state key lasts one invocation,** and what a tool callback writes there is
  visible to the model callback in the same turn.
- **Tools stay unaware of the guard.** It collects numbers from every tool result itself, so
  any tool, skill or MCP result feeds it.
- **The sample guard matches exactly.** "1250.00" from a tool allows "1,250.00", not "1250".

Callback and plugin API: the `google-agents-cli-adk-code` skill.
