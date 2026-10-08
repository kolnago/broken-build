"""Reusable pytest helpers for ADK 2.x (google-adk >= 2.11)."""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator, ClassVar

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.models.registry import LLMRegistry
from google.adk.runners import InMemoryRunner
from google.genai import types


class FakeLlm(BaseLlm):
  """Scripted model. Each item is text, a dict (sent as JSON text), or a
  types.Part (e.g. a function call). Requests are recorded for assertions."""

  def __init__(self, responses: list[Any]):
    super().__init__(model='fake-llm')
    self._responses = list(responses)
    self._requests: list[LlmRequest] = []

  @property
  def requests(self) -> list[LlmRequest]:
    return self._requests

  async def generate_content_async(
      self, llm_request: LlmRequest, stream: bool = False
  ) -> AsyncGenerator[LlmResponse, None]:
    self._requests.append(llm_request)
    item = self._responses.pop(0) if self._responses else 'ok'
    if isinstance(item, types.Part):
      part = item
    elif isinstance(item, (dict, list)):
      part = types.Part(text=json.dumps(item))
    else:
      part = types.Part(text=str(item))
    yield LlmResponse(content=types.Content(role='model', parts=[part]))


class ScriptedLlm(FakeLlm):
  """Fake selected by model *name* ('scripted/<key>'), for agents you cannot
  reach after construction. Workflow copies agents when it is built, so
  `my_agent.model = FakeLlm(...)` after building the graph has no effect.

  Usage:
    model_id = ScriptedLlm.script('ex04', [{'category': 'complaint'}])
    monkeypatch.setenv('ADK_MODEL', model_id)   # read by the agent module
    importlib.reload(agent_module)              # rebuild agents + workflow
  All agents sharing a model id consume one queue in call order.
  """

  scripts: ClassVar[dict[str, list[Any]]] = {}
  calls: ClassVar[dict[str, list[LlmRequest]]] = {}

  def __init__(self, model: str):
    BaseLlm.__init__(self, model=model)
    self._responses = ScriptedLlm.scripts.setdefault(model, [])
    self._requests = ScriptedLlm.calls.setdefault(model, [])

  @classmethod
  def supported_models(cls) -> list[str]:
    return [r'scripted/.*']

  @classmethod
  def script(cls, key: str, responses: list[Any]) -> str:
    model_id = f'scripted/{key}'
    cls.scripts[model_id] = list(responses)
    cls.calls[model_id] = []
    LLMRegistry.register(cls)
    return model_id


def user_msg(text: str) -> types.Content:
  return types.Content(role='user', parts=[types.Part(text=text)])


def node_name(event) -> str | None:
  """'wf@1/step@1' -> 'step'. event.author is the enclosing workflow."""
  if not event.node_info or not event.node_info.path:
    return None
  return event.node_info.path.split('/')[-1].split('@')[0]


def outputs_of(events, name: str) -> list[Any]:
  return [e.output for e in events if node_name(e) == name and e.output is not None]


def pending_request_inputs(events) -> list[types.FunctionCall]:
  return [
      fc for e in events for fc in e.get_function_calls()
      if fc.name == 'adk_request_input'
  ]


def answer(function_call: types.FunctionCall, response: Any) -> types.Content:
  """Builds the user message that resumes a paused RequestInput."""
  payload = response if isinstance(response, dict) else {'result': response}
  return types.Content(role='user', parts=[types.Part(
      function_response=types.FunctionResponse(
          id=function_call.id, name=function_call.name, response=payload))])


async def run_turn(runner: InMemoryRunner, session_id: str, message,
                   user_id: str = 'u1') -> list:
  if isinstance(message, str):
    message = user_msg(message)
  return [e async for e in runner.run_async(
      user_id=user_id, session_id=session_id, new_message=message)]


async def new_session(agent=None, app=None, app_name='test_app', user_id='u1'):
  runner = InMemoryRunner(app=app) if app else InMemoryRunner(
      agent=agent, app_name=app_name)
  name = app.name if app else app_name
  session = await runner.session_service.create_session(
      app_name=name, user_id=user_id)
  return runner, session
