"""ctx.run_node(): loops and branches in plain Python instead of edges."""
from google.adk import Agent, Context, Event, Workflow
from google.adk.workflow import START, node
from pydantic import BaseModel

from ._common import MODEL


class Grade(BaseModel):
  ok: bool
  reason: str


writer = Agent(
    name='writer',
    model=MODEL,
    instruction='Write one headline about "{topic}". Feedback so far: {feedback?}',
)

critic = Agent(
    name='critic',
    model=MODEL,
    mode='single_turn',
    instruction='Is this headline factual and under 12 words?',
    output_schema=Grade,
)


@node(rerun_on_resume=True)  # REQUIRED for any node that calls run_node
async def orchestrate(ctx: Context, node_input: str):
  yield Event(state={'topic': node_input})
  headline = ''
  for i in range(3):
    headline = await ctx.run_node(writer, run_id=f'write-{i}')
    grade = Grade.model_validate(
        await ctx.run_node(critic, node_input=headline, run_id=f'grade-{i}')
    )
    if grade.ok:
      break
    yield Event(state={'feedback': grade.reason})
  yield Event(output=headline)  # generators yield output; never `return x`


root_agent = Workflow(name='dynamic', edges=[(START, orchestrate)])
