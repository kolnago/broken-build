# Agent brick

A model with an instruction and tools. `strict` when its replies pass number verification
before they leave the brick, `free` when its replies are labelled unverified.

## Shape

```
bricks/agents/assistant/agents/analyst/   a part of the assistant (B8); a shared agent sits
├── __init__.py        build_analyst(model, orders): the brick       at bricks/agents/<name>/
├── agent.py           root_agent with default wiring: the entry point for adk
├── prompt.md          the instruction
├── test_analyst.py
└── evals/analyst.evalset.json
```

```python
"""Agent brick, strict. In: a question about orders. Out: an answer whose numbers all come
from tools."""

def build_analyst(model: str | BaseLlm, orders: OrderRepository) -> Agent:
    return Agent(
        name="analyst", model=model, description="...",
        instruction=(Path(__file__).parent / "prompt.md").read_text(),
        tools=[*make_order_tools(orders), order_terms_skills()],   # the tool set lives here
        after_tool_callback=collect_tool_numbers,          # strict: the guard is part of the brick
        after_model_callback=block_invented_numbers,
    )
```

```python
# agent.py
from . import build_analyst

root_agent = build_analyst(
    os.environ.get("ADK_MODEL", "gemini-2.5-flash"), JsonFileOrders(SAMPLE_ORDERS)
)
```

A free agent attaches `label_unverified` instead of the guard.

## Agents working together

An agent that uses other agents is the same shape; its builder calls the other builders.

| Way | Code | Who answers the user |
|---|---|---|
| Hand-over | `sub_agents=[build_analyst(model, orders), build_brainstormer(model)]` | the sub-agent takes over |
| Agent as a tool | `tools=[..., AgentTool(build_brainstormer(model))]` | the parent reads the reply and answers |

Every agent stays a brick with its own `agent.py`, so each one opens alone in `adk web`
whether or not another agent uses it. An agent that only one agent uses is that agent's part
(B8): the sample's analyst lives in `bricks/agents/assistant/agents/analyst/`, the assistant
imports it as `from .agents.analyst import build_analyst`, nothing else may, and it opens
alone with `adk web bricks/agents/assistant/agents`.

A strict agent that uses a free agent as a tool must not take its numbers as fact:

```python
brainstormer = build_brainstormer(model)
return Agent(
    ...,
    tools=[*make_order_tools(orders), AgentTool(brainstormer)],
    after_tool_callback=collect_tool_numbers_except(brainstormer.name),
    after_model_callback=block_invented_numbers,
)
```

## Test

Pass a scripted model as `model`; no reload or patching is needed. `ScriptedModel`, `call`
and `ask` are in [scripted-model.md](scripted-model.md).

```python
model = ScriptedModel([call("get_order_total", order_id="A-1"), "About 1512.50 CZK with tax."])
answer = await ask(build_analyst(model, FakeOrders([order])), "What is the total of order A-1?")
assert "no tool produced" in answer
```

## Eval

A test proves what code guarantees, offline. An eval measures what the prompt achieves with
the real model: which tool it picks for each kind of question.

```json
{"eval_id": "terms", "conversation": [{
  "invocation_id": "terms",
  "user_content": {"role": "user", "parts": [{"text": "When do I have to pay an order?"}]},
  "intermediate_data": {"tool_uses": [{"name": "load_skill", "args": {"skill_name": "order-terms"}}]}}]}
```

One config is shared by all agents, `bricks/agents/eval_config.json`, scoring only the tool
calls: `{"criteria": {"tool_trajectory_avg_score": {"threshold": 1.0, "match_type": "EXACT"}}}`.

```bash
uv run adk eval bricks/agents/assistant/agents/analyst \
  bricks/agents/assistant/agents/analyst/evals/analyst.evalset.json \
  --config_file_path bricks/agents/eval_config.json
```

`adk eval` loads an agent through its `__init__.py`, not through `agent.py`, so the brick
offers the entry point lazily:

```python
async def get_agent_async():
    from .agent import root_agent

    return root_agent, None
```

## Traps

- **The builder takes the model and the ports, and assembles the agent's tools itself.** A
  tool list passed in by each caller was listed twice (in `agent.py` and in the agent that
  composes this one), and a new tool reached only one of them.
- **A new tool needs no prompt line when its docstring says when to use it.** Add a prompt
  line only for what a docstring cannot carry, such as a skill's exact name, or when an eval
  shows the model missing the tool. One live eval confirmed it: a tool added to the factory
  was picked from its docstring alone.
- **The trust mechanism is inside the builder,** so the agent keeps its trust level in
  whatever uses it.
- **The plain number guard trusts every tool result, including a free agent used as a tool.**
  With it, a strict agent repeated the free agent's "15%" as fact. Name the free agent with
  `collect_tool_numbers_except`.
- **An agent tool is called with a free-text `request`,** so an exact tool-call eval cannot
  expect its arguments. The sample's advisor has tests and a live run, and no eval set.
- **In a test, agents sharing one scripted model consume one queue in call order:** parent,
  then the agent tool's reply, then the parent again.
- **Build a new agent on every call.** An ADK agent can have only one parent.
- **ADK imports the folder by its bare name** (`analyst`, not its package path), so
  `agent.py` uses a relative import and the module holds no mutable state.
- **An offline test proves the wiring, not the prompt.** A scripted model always calls the
  right tool; a real one guessed a skill's name wrong. One eval case per kind of question
  covers that.
- **Do not write an eval for what a callback guarantees.** The number guard blocks an invented
  number whatever the model does; that is a test.
- **For an agent of agents, the expected tool calls include the hand-over and the sub-agent's
  calls,** in order: `transfer_to_agent`, then `get_order_total`.
- **Evals need `google-adk[eval]` and a model key, and cost money.** Run them when a prompt,
  a tool's docstring or the model changes.

Agent API, models, state, multi-agent patterns: the `google-agents-cli-adk-code` skill.
