"""Workflows and @node functions passed straight into an agent's tools."""
from google.adk import Agent, Context, Workflow
from google.adk.workflow import START, node
from pydantic import BaseModel, Field

from ._common import MODEL


class LookupArgs(BaseModel):
  customer_id: str = Field(description='Customer identifier.')


def fetch_profile(node_input: LookupArgs) -> dict:
  return {'customer_id': node_input.customer_id, 'segment': 'SME'}


def enrich(node_input: dict) -> dict:
  return {**node_input, 'limit_eur': 50_000}


customer_lookup = Workflow(
    name='customer_lookup',  # tool name
    description='Look up a customer profile and credit limit.',  # tool doc
    input_schema=LookupArgs,  # tool parameters
    edges=[(START, fetch_profile, enrich)],
)


@node
def format_report(case_id: str, ctx: Context) -> str:
  """Formats the final case report verbatim for the user.

  Args:
    case_id: Case identifier.
  """
  ctx.actions.skip_summarization = True  # return as-is, no extra model turn
  return f'Case {case_id}: report ready.'


root_agent = Agent(
    name='analyst',
    model=MODEL,
    instruction='Answer questions using the lookup and report tools.',
    tools=[customer_lookup, format_report],  # auto-wrapped as node tools
)
