# Tools (ADK 2.x)

| Need | Use |
|---|---|
| Simple capability | plain function — name, docstring (`Args:`), type hints are the schema; return `dict`/`str` |
| Context in a tool | parameter `tool_context: ToolContext` (alias of `Context`) |
| Always confirm | `FunctionTool(func=f, require_confirmation=True)` (bool or callable) |
| Confirm conditionally | `tool_context.request_confirmation(hint=...)`; check `tool_context.tool_confirmation.confirmed` |
| Async result | `LongRunningFunctionTool(func=f)` + resumable `App` |
| Workflow as tool | `tools=[my_workflow]` — name/description/`input_schema` from the workflow |
| Function node as tool | `@node`-decorated function in `tools`; `ctx.actions.skip_summarization = True` returns verbatim |
| Typed sub-agent | `sub_agents=[Agent(mode='task', ...)]` (not `tools=[agent]` — rejected) |
| MCP | `McpToolset(connection_params=StdioConnectionParams/SseConnectionParams/StreamableHTTPConnectionParams(...), tool_filter=[...], tool_name_prefix=...)` — needs `google-adk[mcp]` |
| REST | `OpenAPIToolset(spec_str=..., spec_str_type='json' or 'yaml', auth_scheme=..., auth_credential=..., tool_filter=...)` |
| Consult a stronger model | `ModelConsultTool(max_uses=2, session_max_uses=5, thinking_level='high')` (2.11) |
| Agent skills | `SkillToolset(skills=[load_skill_from_dir(path)], additional_tools=[...])` |
| Memory | `load_memory` (model-driven), `preload_memory` (automatic) from `google.adk.tools` |
| Custom tool | subclass `BaseTool`: `_get_declaration()` + `async run_async(*, args, tool_context)` |
| Custom toolset | subclass `BaseToolset`: `async get_tools(readonly_context)` |

Imports:

```python
from google.adk.tools import FunctionTool, LongRunningFunctionTool, ToolContext, BaseTool, ModelConsultTool, load_memory, preload_memory
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams, SseConnectionParams, StreamableHTTPConnectionParams
from google.adk.tools.openapi_tool import OpenAPIToolset
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.skills import load_skill_from_dir
```

Import MCP lazily (inside a function) if the module must load without the
`[mcp]` extra. `MCPToolset` (caps) is deprecated. Allow-list tools with
`tool_filter` for anything that can write. Since 2.7 tools can return media
(images) back to the model.
