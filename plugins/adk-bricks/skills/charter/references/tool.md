# Tool brick

A function a model can call. Strict by construction: it returns what code computed.

## Shape

```
bricks/tools/order_tools/
├── __init__.py            a factory that returns the tool functions
└── test_order_tools.py
```

```python
def make_order_tools(orders: OrderRepository) -> list[Callable[..., dict]]:
    def get_order_total(order_id: str) -> dict:
        """Returns the exact total of one order. Use it whenever the user asks what an
        order costs or adds up to. Never work a total out yourself.

        Args:
            order_id: The order's identifier, for example "A-1".

        Returns:
            status "ok" with the total as a decimal string and its currency, or
            status "error" with a message to pass on to the user.
        """
        try:
            total = order_total(orders.get(order_id))
        except OrderNotFound:
            return {"status": "error", "message": f"There is no order {order_id}."}
        return {"status": "ok", "order_id": order_id, "total": str(total.amount),
                "currency": total.currency}

    return [get_order_total]
```

## Test

Call the functions directly with a fake repository. No ADK and no model are involved.

## Traps

- **The factory takes the port** (B4), so the same tools run against a file, a database or a
  fake, and an [MCP server](mcp-server.md) can serve the very same functions.
- **The docstring is the model's only instruction for the tool.** Say when to use it and what
  not to do.
- **Parameters are primitives; amounts go out as decimal strings,** never `float`.
- **A domain error is a returned `status: "error"`,** not an exception, so the model can tell
  the user. That includes a calculator's `ValueError` for input that has no answer.
- **A second tool on the same port and topic goes into the same factory.** Tests pick tools by
  name (`{tool.__name__: tool for tool in make_order_tools(orders)}`), never by position, so
  adding one breaks nothing.
- **To give an agent a new tool, add it to that agent's builder.** Nothing else lists tools.
- **A tool never computes.** It fetches through the port and calls a
  [calculator](calculator.md).

ADK tool API (toolsets, `ToolContext`, confirmation): the `google-agents-cli-adk-code` skill.
