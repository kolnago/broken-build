"""Typed function-node pipeline: Pydantic in/out, UI message vs output, state."""
from google.adk import Event, Workflow
from google.adk.workflow import START
from pydantic import BaseModel


class Ticket(BaseModel):
  text: str
  words: int


def parse(node_input: str) -> Ticket:
  # START without input_schema hands over types.Content; a `str` annotation
  # coerces it to the message text. A returned model is dumped to a dict.
  return Ticket(text=node_input, words=len(node_input.split()))


def prioritise(node_input: Ticket):
  # The dict from `parse` is coerced back into Ticket by the annotation.
  p = 'high' if 'outage' in node_input.text.lower() else 'normal'
  # One event may carry output + state; state lands in
  # event.actions.state_delta (replay-safe), unlike ctx.state[...] = ...
  return Event(output={'ticket': node_input.model_dump(), 'priority': p},
               state={'last_priority': p})


def report(node_input: dict):
  # Generator node: yield (never `return value`). At most one output event.
  text = f"[{node_input['priority']}] {node_input['ticket']['text']}"
  yield Event(message=text)  # rendered in adk web (event.content)
  yield Event(output=text)   # passed downstream / workflow output


root_agent = Workflow(name='ticket_pipeline',
                      edges=[(START, parse, prioritise, report)])
