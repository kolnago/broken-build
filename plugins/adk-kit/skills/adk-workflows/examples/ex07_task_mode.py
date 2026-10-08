"""Coordinator delegating to schema-typed sub-agents (task / single_turn)."""
from google.adk import Agent
from pydantic import BaseModel, Field

from ._common import MODEL


class CaseInput(BaseModel):
  case_id: str = Field(description='Limit-overdraft case identifier.')


class CaseFindings(BaseModel):
  summary: str
  risk_level: str = Field(description='low | medium | high')
  open_questions: list[str] = []


def get_case(case_id: str) -> dict:
  """Fetches the case facts for a limit-overdraft case."""
  return {'case_id': case_id, 'limit': 50_000, 'exposure': 61_200}


investigator = Agent(
    name='investigator',
    mode='task',  # may ask the user follow-ups; ends by calling finish_task
    description='Investigates one limit-overdraft case and returns findings.',
    input_schema=CaseInput,
    output_schema=CaseFindings,
    instruction=(
        'Use get_case, reason about the overdraft, ask the user if facts are'
        ' missing, then call finish_task with your findings.'
    ),
    tools=[get_case],
)


class Summary(BaseModel):
  text: str


summariser = Agent(
    name='summariser',
    mode='single_turn',  # autonomous: told no user replies will come
    description='Writes a 3-sentence management summary of findings.',
    output_schema=Summary,
    instruction='Summarise the findings in three sentences, then finish_task.',
)

root_agent = Agent(
    name='coordinator',
    model=MODEL,  # sub-agents inherit the nearest ancestor's model
    instruction=(
        'Call investigator for a case, then summariser on its findings.'
        ' Call one delegation tool at a time.'
    ),
    sub_agents=[investigator, summariser],  # exposed as tools named by `name`
)
