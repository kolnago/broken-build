# Surface brick

A2UI messages that draw a piece of UI, built in code. Strict by construction: the layout is
fixed and every amount is produced by a calculator.

## Shape

```
modules/orders/surfaces/order_card/
├── __init__.py            docstring; from .order_card import order_card; __all__
├── order_card.py          order_card(order, total): returns the list of messages
├── _components.py         the layout constant
└── test_order_card.py
```

```python
# order_card.py
def order_card(order: Order, total: Money) -> list[dict]:
    surface_id = f"order-{order.order_id}"
    data = {"title": f"Order {order.order_id}", "lines": [...], "total": display(total)}
    return [
        {"version": "v0.9", "createSurface": {"surfaceId": surface_id, "catalogId": BASIC_CATALOG}},
        {"version": "v0.9", "updateComponents": {"surfaceId": surface_id, "components": COMPONENTS}},
        {"version": "v0.9", "updateDataModel": {"surfaceId": surface_id, "path": "/", "value": data}},
    ]
```

`COMPONENTS` is a constant: a flat list of `{"id", "component", ...}` with one `root`, values
bound by `{"path": "/total"}`, and lists as `{"componentId": "line", "path": "/lines"}`.

A tool returns the surface in its result, and the frontend draws it:

```python
return {"status": "rendered", "order_id": order_id, "total": str(total.amount),
        "currency": total.currency, "a2ui": order_card(order, total)}
```

## Test

The data model equals the expected formatted strings; every child a component names exists;
the layout contains no digits.

## Traps

- **Amounts reach the screen as formatted strings** through the data model. The browser never
  formats or adds a number.
- **Arithmetic for the surface belongs in a [calculator](calculator.md).** The card's line
  totals come from `line_total`.
- **The tool's docstring tells the model the card is already shown,** so it does not repeat
  the contents.
- **No custom server is needed.** ADK's server streams the tool result; the frontend reads
  `functionResponse.response.a2ui` and gives it to one message processor per answer.
- **Versions proven together:** protocol v0.9, `@a2ui/react` 0.11.1, `@a2ui/web_core` 0.11.0,
  the basic catalog.
- **A surface belongs to the module whose data it shows.** A case card lives with the case,
  not in a `ui` module.

Not proven here: a layout written by a model (it needs validation before it leaves the
server) and user actions sent back from a surface.
