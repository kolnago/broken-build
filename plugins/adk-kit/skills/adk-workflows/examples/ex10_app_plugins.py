"""App with a plugin, an agent callback guardrail, retries and timeouts."""
import logging
from typing import Any

from google.adk import Agent, Context, Workflow
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins import BasePlugin
from google.adk.tools import BaseTool, ToolContext
from google.adk.workflow import START, RetryConfig, node
from google.genai import types

from ._common import MODEL

log = logging.getLogger(__name__)


class AuditPlugin(BasePlugin):
  """App-wide hooks. Return None to continue, a value to short-circuit."""

  def __init__(self) -> None:
    super().__init__(name='audit')
    self.tool_calls: list[str] = []

  async def before_tool_callback(
      self, *, tool: BaseTool, tool_args: dict[str, Any],
      tool_context: ToolContext) -> dict | None:
    self.tool_calls.append(tool.name)
    log.info('tool %s args=%s', tool.name, tool_args)
    return None


def block_iban_in_prompt(callback_context: CallbackContext,
                         llm_request: LlmRequest) -> LlmResponse | None:
  """Agent-level guardrail: skip the model call if the prompt has an IBAN."""
  for content in llm_request.contents:
    for part in content.parts or []:
      if part.text and 'CZ65' in part.text:
        return LlmResponse(content=types.ModelContent(
            'I cannot process account numbers here.'))
  return None


def lookup_rate(currency: str) -> dict:
  """Returns the FX rate to EUR for a currency code."""
  return {'currency': currency, 'eur': 0.04}


assistant = Agent(
    name='assistant',
    model=MODEL,
    instruction='Answer FX questions with lookup_rate.',
    tools=[lookup_rate],
    before_model_callback=block_iban_in_prompt,
)


@node(retry_config=RetryConfig(max_attempts=3, initial_delay=0.01,
                               exceptions=[ConnectionError]),
      timeout=10.0)
def flaky_fetch(ctx: Context, node_input: str) -> str:
  # attempt_count is 1 on the first try. Keep side effects idempotent: since
  # 2.9 a failed node runs again when the workflow resumes.
  if ctx.attempt_count < 2:
    raise ConnectionError('upstream hiccup')
  return f'{node_input} (fetched on attempt {ctx.attempt_count})'


pipeline = Workflow(name='pipeline', edges=[(START, flaky_fetch)])

audit = AuditPlugin()
app = App(name='fx_app', root_agent=assistant, plugins=[audit])
pipeline_app = App(name='pipeline_app', root_agent=pipeline)
root_agent = assistant
