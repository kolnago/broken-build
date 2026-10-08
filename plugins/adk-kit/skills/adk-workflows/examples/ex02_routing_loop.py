"""Conditional routing, DEFAULT_ROUTE and a bounded self-loop."""
from google.adk import Context, Event, Workflow
from google.adk.workflow import DEFAULT_ROUTE, START


def classify(node_input: str):
  text = node_input.lower()
  if 'refund' in text:
    route = 'refund'
  elif 'fraud' in text:
    route = 'fraud'
  else:
    route = 'other'
  return Event(output=node_input, route=route)


def handle_refund(node_input: str) -> str:
  return f'refund queue: {node_input}'


def handle_fraud(node_input: str) -> str:
  return f'fraud desk: {node_input}'


def fallback(node_input: str) -> str:
  return f'general queue: {node_input}'


def retry_until_done(ctx: Context, node_input: str):
  # Self-loop: a cycle is legal only if at least one edge in it is routed.
  attempt = ctx.state.get('attempt', 0) + 1
  if attempt < 3:
    return Event(output=node_input, route='again', state={'attempt': attempt})
  return Event(output=f'{node_input} (after {attempt} passes)', route='done',
               state={'attempt': attempt})


def finish(node_input: str) -> str:
  return node_input


root_agent = Workflow(
    name='router',
    edges=[
        (START, classify),
        # Every outgoing edge of a routing node carries a route; an unrouted
        # edge would fire on every output in addition to the chosen branch.
        (classify, {
            'refund': handle_refund,
            'fraud': handle_fraud,
            DEFAULT_ROUTE: fallback,
        }),
        ((handle_refund, handle_fraud, fallback), retry_until_done),
        (retry_until_done, {'again': retry_until_done, 'done': finish}),
    ],
)
