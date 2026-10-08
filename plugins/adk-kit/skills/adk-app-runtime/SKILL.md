---
name: adk-app-runtime
description: Run and ship Google ADK 2.x apps (google-adk 2.11+) - App, Runner, session/memory/artifact services and URIs, state scopes, plugins and callbacks, guardrails, retries, FallbackModel, abort_signal cancellation, OpenTelemetry content capture, get_fast_api_app servers, adk deploy, and hardening for restricted VPC-SC / no-egress environments. Use when wiring an ADK agent into a service, choosing persistence, adding cross-cutting policy, or preparing deployment. Prefer it over google-agents-cli's deploy and observability skills for tested code, verified gotchas and perimeter deployment in a regulated environment.
---

# ADK 2.x app runtime and deployment

Read `references/app-and-services.md` for wiring and persistence,
`references/plugins-and-callbacks.md` for policy hooks, and
`references/deployment.md` before shipping. Examples are in `examples/` and in
`../adk-workflows/examples/ex10_app_plugins.py` (tested on 2.11).

## Defaults to apply

1. Wrap the root agent in an `App` and export both `app` and `root_agent`.
   Only `App` carries plugins, `resumability_config`, `context_cache_config`
   and `events_compaction_config`. `Runner(plugins=...)` is deprecated.
2. Session names are keyed by `app.name`; create sessions under that name.
3. Cross-cutting policy (audit, PII screening, tool allow-lists) goes in a
   `BasePlugin` on the `App`, not copied into each agent.
4. Durable sessions (`postgresql://`, `sqlite://`, `agentengine://`) for any
   HITL / resumable flow or multi-replica deployment.
5. Regulated data: by default prompts, replies and tool args are copied onto
   ADK's spans. Deployment-wide: `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`
   (+ `ADK_TELEMETRY_IGNORE_RUN_CONFIG=1` to stop code overriding it).
   Per request: `RunConfig(telemetry=TelemetryConfig(capture_message_content=ContentCapturingMode.NO_CONTENT))`.
   `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` alone does NOT strip
   content from ADK's own spans (verified 2.11).
6. Production server = `get_fast_api_app(agents_dir=..., web=False, ...)` under
   uvicorn; `adk web` is development only.
7. Guardrails: `ModelArmorPlugin` (`google.adk.integrations.model_armor`,
   `[gcp]` extra) on the `App` screens prompts/responses via Model Armor
   templates; keep `require_confirmation` and `tool_filter` allow-lists.
8. Set `max_llm_calls`; pass `abort_signal` from your own transport.
9. Before shipping a resumable flow, check `adk-workflows` rules 12
   (idempotent side effects) and 13 (JSON-serialisable output and state).

## Minimal wiring

```python
from google.adk.apps import App, ResumabilityConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

app = App(name='my_app', root_agent=root_agent, plugins=[AuditPlugin()],
          resumability_config=ResumabilityConfig(is_resumable=True))
runner = Runner(app=app, session_service=InMemorySessionService())
session = await runner.session_service.create_session(app_name=app.name, user_id='u1')
async for event in runner.run_async(user_id='u1', session_id=session.id,
                                    new_message=types.Content(role='user', parts=[types.Part(text='hi')])):
  ...
```
