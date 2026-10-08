"""Tool catalogue for ADK 2.x: functions, confirmation, MCP, long-running."""
from google.adk import Agent
from google.adk.tools import FunctionTool, LongRunningFunctionTool, ToolContext

from ._common import MODEL


def get_exposure(customer_id: str, tool_context: ToolContext) -> dict:
  """Returns current credit exposure for a customer.

  Args:
    customer_id: Customer identifier, e.g. 'C-123'.
  """
  # Name, docstring and type hints ARE the schema the model sees.
  # A `tool_context` parameter is injected (ToolContext is an alias of Context).
  tool_context.state['last_customer'] = customer_id
  return {'customer_id': customer_id, 'exposure_eur': 61_200}


def raise_limit(customer_id: str, new_limit_eur: int,
                tool_context: ToolContext) -> dict:
  """Raises a customer's credit limit (needs human confirmation above 10k)."""
  if new_limit_eur > 10_000:
    if not tool_context.tool_confirmation:
      tool_context.request_confirmation(
          hint=f'Raise limit of {customer_id} to EUR {new_limit_eur}?')
      return {'status': 'pending confirmation'}
    if not tool_context.tool_confirmation.confirmed:
      return {'status': 'rejected by user'}
  return {'status': 'done', 'new_limit_eur': new_limit_eur}


def block_card(card_id: str) -> dict:
  """Blocks a payment card. Destructive."""
  return {'status': 'blocked', 'card_id': card_id}


def open_review_ticket(case_id: str) -> dict:
  """Opens a manual review ticket; the result arrives later."""
  return {'status': 'queued', 'ticket': f'T-{case_id}'}


def mcp_tools():
  """MCP needs `pip install google-adk[mcp]`. Imported lazily on purpose."""
  from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
  return McpToolset(
      connection_params=StreamableHTTPConnectionParams(
          url='http://localhost:3000/mcp'),
      tool_filter=['read_file', 'list_directory'],  # allow-list read-only tools
      tool_name_prefix='fs',
  )


root_agent = Agent(
    name='credit_ops',
    model=MODEL,
    instruction='Help credit officers. Never raise limits without confirmation.',
    tools=[
        get_exposure,                                          # auto FunctionTool
        raise_limit,                                           # conditional confirm
        FunctionTool(func=block_card, require_confirmation=True),  # always confirm
        LongRunningFunctionTool(func=open_review_ticket),      # pauses the agent
    ],
)
