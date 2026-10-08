"""RequestInput pause/resume with a resumable App and a per-iteration id."""
from typing import Any

from google.adk import Context, Event, Workflow
from google.adk.apps import App, ResumabilityConfig
from google.adk.events import RequestInput
from google.adk.workflow import START, node
from pydantic import BaseModel


class Decision(BaseModel):
  approved: bool
  # Resume answers can arrive with absent keys filled as None: make
  # optional fields Optional, not defaulted non-null strings.
  comment: str | None = None


def draft(ctx: Context, node_input: str):
  # On a 'revise' loop node_input is the previous draft, so keep the original
  # request in state (written via Event(state=...) so replay reproduces it).
  request = ctx.state.get('request') or node_input
  n = ctx.state.get('review_round', 0)
  return Event(output=f'Draft v{n + 1}: {request}', state={'request': request})


@node(rerun_on_resume=True)  # re-run on resume; answers in ctx.resume_inputs
async def review(ctx: Context, node_input: Any):
  round_no = ctx.state.get('review_round', 0)
  interrupt_id = f'review_{round_no}'  # unique per loop iteration
  answer = ctx.resume_inputs.get(interrupt_id)
  if answer is None:
    yield RequestInput(
        interrupt_id=interrupt_id,
        message=f'Approve this?\n\n{node_input}',
        payload={'draft': node_input},
        response_schema=Decision,
    )
    return
  decision = Decision.model_validate(answer)
  yield Event(
      output=node_input,
      route='approved' if decision.approved else 'revise',
      state={'review_round': round_no + 1},
  )


def publish(node_input: str) -> str:
  return f'PUBLISHED: {node_input}'


root_agent = Workflow(
    name='approval_flow',
    edges=[
        (START, draft, review),
        (review, {'approved': publish, 'revise': draft}),
    ],
)

# Resumable: checkpoints workflow progress and resumes at the paused node
# instead of replaying from START. Export both `app` and `root_agent`.
app = App(
    name='approval_app',
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)
