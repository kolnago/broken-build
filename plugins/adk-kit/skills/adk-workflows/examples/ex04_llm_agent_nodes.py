"""LlmAgent as a workflow node: output_schema, state placeholders, output_key."""
from google.adk import Agent, Event, Workflow
from google.adk.workflow import START
from pydantic import BaseModel

from ._common import MODEL


class Classification(BaseModel):
  category: str
  confidence: float


def remember_topic(node_input: str):
  # Instructions read {placeholders} from state only, never from node_input.
  return Event(output=node_input, state={'domain': 'retail banking'})


classifier = Agent(
    name='classifier',
    model=MODEL,
    # Auto-wrapped agents default to mode='single_turn' (no chat history).
    instruction=(
        'Classify the customer message for the {domain} domain into one of:'
        ' complaint, question, request.'
    ),
    output_schema=Classification,  # next node gets a dict
    output_key='classification',   # also stored in state (as a dict)
)


def route_on_class(node_input: dict):
  return Event(output=node_input, route=node_input['category'])


responder = Agent(
    name='responder',
    model=MODEL,
    instruction=(
        'Draft a short, polite reply. Context: {classification?}'
    ),  # {key?} -> empty string when missing; {key} raises KeyError
)


def escalate(node_input: dict) -> str:
  return f"Escalated complaint (confidence {node_input['confidence']:.2f})"


root_agent = Workflow(
    name='llm_nodes',
    edges=[
        (START, remember_topic, classifier, route_on_class),
        (route_on_class, {
            'complaint': escalate,
            'question': responder,
            'request': responder,
        }),
    ],
)
