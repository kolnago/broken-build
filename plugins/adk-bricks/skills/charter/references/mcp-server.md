# MCP server brick

Tools behind a process boundary, usable from ADK and from any other MCP client. Strict by
construction when it serves tool bricks.

## Shape

```
bricks/mcp/orders_server/
├── __init__.py              build_server(orders): the brick
├── __main__.py              runs it over stdio with default wiring: the entry point
└── test_orders_server.py
```

```python
from mcp.server.mcpserver import MCPServer

SERVED = ["get_order_total"]

def build_server(orders: OrderRepository) -> MCPServer:
    server = MCPServer(name="orders")
    for tool in make_order_tools(orders):
        if tool.__name__ in SERVED:
            server.add_tool(tool)
    return server
```

```python
# __main__.py
build_server(JsonFileOrders(SAMPLE_ORDERS)).run("stdio")
```

Run it with `uv run python -m bricks.mcp.orders_server`.

## Test

In process, and once over stdio through ADK's own client:

```python
result = await build_server(ORDERS).call_tool("get_order_total", {"order_id": "A-1"})
assert json.loads(result.content[0].text)["total"] == "1250.00"

toolset = McpToolset(connection_params=StdioConnectionParams(server_params=StdioServerParameters(
    command=sys.executable, args=["-m", "bricks.mcp.orders_server"])))
try:
    assert [tool.name for tool in await toolset.get_tools()] == ["get_order_total"]
finally:
    await toolset.close()
```

## Traps

- **Install `google-adk[mcp]`.** Without the extra, `McpToolset` cannot be imported.
- **MCP 2 renamed `FastMCP` to `MCPServer`** (`mcp.server.mcpserver`). Checked on `mcp` 2.3.0.
- **A tool returning a plain `dict` arrives as JSON text** in `content[0].text`;
  `structured_content` is empty.
- **Serve the same functions the agents use,** from the tool brick's factory, and name what
  is served in an allow-list. A tool that returns a surface is not served.
- **Close the toolset in the test,** or the server process outlives it.

MCP toolsets and remote servers: the `google-agents-cli-adk-code` skill.
