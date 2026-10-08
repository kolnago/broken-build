# Workflow brick

A graph of nodes with fixed control flow. Without a model in it, it is strict by construction
and runs without a key.

## Shape

```
modules/orders/workflows/order_lookup/
├── __init__.py            docstring; from .builder import build_order_lookup; __all__
├── builder.py             build_order_lookup(orders): the brick
├── agent.py               root_agent with default wiring
└── test_order_lookup.py
```

```python
# builder.py
def build_order_lookup(orders: OrderRepository) -> Workflow:
    def find_order(node_input: str) -> Event:
        found = _ORDER_ID.search(node_input)
        if found is None:
            return Event(output=node_input, route="no_id")
        return Event(output=found.group(), route="found")

    def report_total(node_input: str) -> Event:
        ...
        return Event(message=f"Order {node_input} comes to {display(total)}.")

    return Workflow(
        name="order_lookup", description="...",
        edges=[(START, find_order), (find_order, {"found": report_total, "no_id": ask_for_id})],
    )
```

Imports: `from google.adk import Event, Workflow` and `from google.adk.workflow import START`.

## Test

Run one turn and compare the text; no scripted model is needed when no node has a model.

```python
assert await ask(build_order_lookup(ORDERS), "what does A-1 cost?") == "Order A-1 comes to 1,250.00 CZK."
```

## Traps

- **Annotate `node_input: str` on the first node** to receive the user's text; without it the
  node gets a `Content` object.
- **`Event(output=...)` feeds the next node; `Event(message=...)` is what the user sees.**
- **Every edge leaving a routing node carries a route.**
- **A workflow is a `root_agent` like any agent,** so `adk web` and `adk run` run it. It
  lives in its module's `workflows/`; an [app](app.md) serves it once the app's server names it.
- **Nodes close over the port** passed to the builder (B4).
- **A workflow of agents calls their builders** inside its own builder, like an agent of
  agents; agents from other modules arrive through those modules' exports (M2).

Workflow API (loops, fan-out and join, `RequestInput`, retries): the
`google-agents-cli-adk-code` skill, `references/adk-python-workflows.md`.
