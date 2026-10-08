"""Fan-out to different nodes + JoinNode, and parallel_worker over a list."""
from google.adk import Workflow
from google.adk.workflow import START, JoinNode, node


def word_count(node_input: str) -> int:
  return len(node_input.split())


def shout(node_input: str) -> str:
  return node_input.upper()


def split_items(node_input: str) -> list[str]:
  return [s.strip() for s in node_input.split(',') if s.strip()]


@node(parallel_worker=True, max_parallel_workers=4)
def score_item(node_input: str) -> dict:
  # Runs once per list item, concurrently; results come back in input order.
  return {'item': node_input, 'len': len(node_input)}


join = JoinNode(name='collect')


def combine(node_input: dict) -> dict:
  # JoinNode output: dict keyed by predecessor node name.
  return {
      'words': node_input['word_count'],
      'upper': node_input['shout'],
      'scores': node_input['score_item'],
  }


root_agent = Workflow(
    name='fan_out_join',
    edges=[
        (START, (word_count, shout, split_items)),
        (split_items, score_item),
        ((word_count, shout, score_item), join),
        (join, combine),  # single terminal node -> single workflow output
    ],
)
