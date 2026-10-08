---
name: adk-testing
description: Test and evaluate Google ADK 2.x agents and workflows (google-adk 2.11+) - offline pytest with InMemoryRunner and a scripted fake model, asserting node outputs, routing, state and human-in-the-loop resume, golden replay tests with `adk test`, and quality evals with `adk eval` / AgentEvaluator. Use when adding tests to an ADK agent, debugging why a test sees the wrong events, or setting up CI and eval criteria. Prefer it over google-agents-cli's eval skill when you need tested pytest helpers, framework canaries and verified gotchas.
---

# Testing ADK 2.x agents

Three layers, cheapest first:

| Layer | Tool | Model needed |
|---|---|---|
| Unit / graph | pytest + `InMemoryRunner` + `FakeLlm` / `ScriptedLlm` (`examples/adk_test_helpers.py`) | no |
| Golden replay | `adk test <agents_dir>` over `<agent>/tests/*.json`; `--rebuild` re-records | only to record |
| Quality eval | `adk eval <agent_dir> <set>.evalset.json --config_file_path eval_config.json`, or `AgentEvaluator.evaluate(...)` in pytest | yes |

## Start

1. Copy `examples/adk_test_helpers.py`, `examples/conftest.py` pattern and
   `examples/pytest.ini` (`asyncio_mode = auto`) into the project's tests.
2. Make the model name injectable so tests can swap in `ScriptedLlm` by name.
   The examples read `ADK_MODEL` in `_common.py`; the fallback name there is a
   placeholder for the examples, not a recommendation. In an `adk-architecture`
   project the name is a `Settings` field in `config.py` (CFG-1: no
   `os.environ` elsewhere): the test sets the env var that field reads, clears
   the cached settings and reloads the agent module.
3. Copy the closest test from `examples/test_examples.py` (17 tests: 4 are
   framework canaries for behaviours the skills rely on; the rest cover
   pipeline, routing, fan-out/join, LLM nodes, HITL loops, dynamic nodes, task
   mode, node-as-tool, tool confirmation, plugins/callbacks/retry, abort).

## Patterns

```python
# Pure graph, no model
runner, s = await new_session(root_agent)
ev = await run_turn(runner, s.id, 'hello')
assert outputs_of(ev, 'final_node') == ['expected']

# Agents: script model responses in call order (text, dict→JSON, or fc(...) Part)
model_id = ScriptedLlm.script('case1', [fc('lookup', id='1'), 'Answer.'])
monkeypatch.setenv('ADK_MODEL', model_id)
mod = importlib.reload(importlib.import_module('my_app.agent'))
calls = ScriptedLlm.calls[model_id]          # recorded LlmRequests

# Human in the loop
fc_ = pending_request_inputs(ev)[0]           # adk_request_input call
ev = await run_turn(runner, s.id, answer(fc_, {'approved': True}))

# Tool confirmation
conf = [c for e in ev for c in e.get_function_calls() if c.name == 'adk_request_confirmation']
ev = await run_turn(runner, s.id, answer(conf[0], {'confirmed': True}))

# State after the run
got = await runner.session_service.get_session(app_name='test_app', user_id='u1', session_id=s.id)
```

## Traps

The ADK behaviour behind each trap is stated once, in `adk-workflows`; here is
what to do about it in a test.

- `agent.model = FakeLlm(...)` after the graph is built is ignored (its rule 14).
  Inject by model name and reload, or build agents inside the test.
- Find the emitting node with the `node_name()` helper, not `event.author`, and
  assert an LLM node's result downstream, on `state[output_key]` or on
  `event.content` (its `references/nodes-events-context.md`: Event, LlmAgent
  as a node).
- Give resume-answer models Optional fields (its `references/human-in-the-loop.md`).
- One runner + session + unique `app_name` per test. Add one test on
  `sqlite://` for graphs with `JoinNode` or HITL: in-memory sessions hide the
  serialisation errors of its rule 13.
- Use `InMemoryRunner(app=app)` (not the bare agent) when the behaviour depends
  on plugins or resumability.

In an `adk-architecture` project, its TEST-1..4 say what to assert (never a
number an LLM produced; tool choice, cited figures, flag consistency); this
skill is how. The graph patterns under test are in `adk-workflows`.

See `references/eval-and-replay.md` for `adk test` and `adk eval` details.
