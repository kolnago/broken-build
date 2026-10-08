# Plugins and callbacks (ADK 2.x)

Contract: return `None` to continue; return a value to replace the step.

| Hook | Return to override |
|---|---|
| `before_agent_callback(callback_context)` / `after_agent_callback` | `types.Content` |
| `before_model_callback(callback_context, llm_request)` / `after_model_callback(callback_context, llm_response)` | `LlmResponse` |
| `on_model_error_callback(callback_context, llm_request, error)` | `LlmResponse` |
| `before_tool_callback(tool, args, tool_context)` / `after_tool_callback(tool, args, tool_context, tool_response)` | `dict` |
| `on_tool_error_callback(tool, args, tool_context, error)` | `dict` |

Agent callbacks may be sync or async, single or a list (first non-None wins).
Plugin methods are async and keyword-only (`tool_args=` not `args=` in
`before_tool_callback`), plus plugin-only hooks: `on_user_message_callback`,
`before_run_callback`, `on_event_callback`, `after_run_callback`,
`on_agent_error_callback`, `on_run_error_callback`.

```python
from google.adk.plugins import BasePlugin

class AuditPlugin(BasePlugin):
  def __init__(self):
    super().__init__(name='audit')

  async def before_tool_callback(self, *, tool, tool_args, tool_context):
    log.info('tool %s %s', tool.name, tool_args)
    return None
```

Built-ins: `google.adk.plugins` exports `LoggingPlugin`, `DebugLoggingPlugin`,
`ReflectAndRetryToolPlugin`, `ReflectAndRetryModelPlugin`,
`ToolCallIntegrityPlugin`. Modules under `google.adk.plugins.`:
`context_filter_plugin.ContextFilterPlugin(num_invocations_to_keep=N)`,
`global_instruction_plugin.GlobalInstructionPlugin`,
`save_files_as_artifacts_plugin.SaveFilesAsArtifactsPlugin`,
`multimodal_tool_results_plugin.MultimodalToolResultsPlugin`,
`bigquery_agent_analytics_plugin.BigQueryAgentAnalyticsPlugin`
(`[bigquery-analytics]` extra). CLI: `--extra_plugins`.

Model Armor: `from google.adk.integrations.model_armor import ModelArmorPlugin, ModelArmorConfig`
(`[gcp]` extra); `App(plugins=[ModelArmorPlugin(config=ModelArmorConfig(
prompt_template_name=..., response_template_name=...))])`.

Workflow tool nodes run plugin tool callbacks too (2.11).
