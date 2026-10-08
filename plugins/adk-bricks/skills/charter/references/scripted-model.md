# Scripted model

A fake model for offline tests of agents, kept as a brick in `bricks/fakes/scripted_model/`.
It replies with what the test scripted, in order, and records the requests it received.

```python
class ScriptedModel(BaseLlm):
    def __init__(self, replies: list[Any]):
        super().__init__(model="scripted")
        self._replies = list(replies)
        self._requests: list[LlmRequest] = []

    async def generate_content_async(self, llm_request, stream=False):
        self._requests.append(llm_request)
        reply = self._replies.pop(0) if self._replies else "ok"
        part = reply if isinstance(reply, types.Part) else types.Part(text=str(reply))
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def call(name: str, **args: Any) -> types.Part:
    """A model reply that calls a tool."""
    return types.Part(function_call=types.FunctionCall(name=name, args=args))


async def ask(agent, question: str) -> str:
    """Runs one turn against an agent and returns the text the user would see."""
    runner = InMemoryRunner(agent=agent, app_name="test")
    session = await runner.session_service.create_session(app_name="test", user_id="u1")
    message = types.Content(role="user", parts=[types.Part(text=question)])
    texts = []
    async for event in runner.run_async(user_id="u1", session_id=session.id, new_message=message):
        if event.content and event.content.parts:
            texts += [part.text for part in event.content.parts if part.text]
    return "\n".join(texts)
```

Imports: `BaseLlm` from `google.adk.models.base_llm`, `LlmRequest` and `LlmResponse` from
`google.adk.models.llm_request` and `.llm_response`, `InMemoryRunner` from
`google.adk.runners`, `types` from `google.genai`. Tests are `async def` and run with
`pytest-asyncio` in `asyncio_mode = "auto"`.

## Uses

- **An agent's test:** script a tool call, then the final text.
- **An agent of agents:** script `call("transfer_to_agent", agent_name="analyst")` first; all
  agents built with the same model instance consume one queue in call order.
- **Looking at a frontend without a key:** an entry point under `spikes/` builds an agent with
  a scripted model that repeats its script, and the app serves that folder.

## Limits

It proves that tools, callbacks and routing are wired correctly. It proves nothing about the
prompt: a scripted model always makes the call the test wrote.
