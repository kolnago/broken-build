# Deployment and restricted environments (ADK 2.x)

| Target | Command | Notes |
|---|---|---|
| Cloud Run | `adk deploy cloud_run --project P --region R [--with_ui] [--a2a] [--session_service_uri ...]` | uses Cloud Build + image pulls |
| Agent Runtime (formerly Vertex AI Agent Engine) | `adk deploy agent_engine ...` | managed sessions / Memory Bank; Cloud Build worker pools (2.8+) |
| GKE | `adk deploy gke ...` | |
| Docker | `adk deploy docker` | generates a Dockerfile you can adapt |
| Own server | `get_fast_api_app(agents_dir=..., web=False)` + uvicorn | recommended behind a perimeter |

`get_fast_api_app` keyword args (2.11): `agents_dir`, `web` (required),
`session_service_uri`, `session_db_kwargs`, `artifact_service_uri`,
`memory_service_uri`, `use_local_storage`, `eval_storage_uri`, `allow_origins`,
`a2a`, `task_store_uri`, `host`, `port`, `url_prefix`, `trace_to_cloud`,
`otel_to_cloud`, `reload_agents`, `lifespan`, `extra_plugins`,
`auto_create_session`, `trigger_sources`, `default_llm_model`,
`max_llm_calls`. The app already serves `/health` and `/version`, plus
`/list-apps`, `/run`, `/run_sse` and the session endpoints.

## Official networking rules (docs.cloud.google.com, checked 2026-10-02)

| Target | Requirement |
|---|---|
| Agent Runtime | Project inside the VPC-SC perimeter **before** first deploy (else the agent stays unprotected with internet access) |
| Agent Runtime | Egress via PSC interface network attachment, min /28 subnet per project, internet only through a proxy in your VPC (+ Cloud NAT); PSC-I disables direct internet egress |
| Agent Runtime | Shared VPC supported (attachment in the service project); restricted services incl. `aiplatform`, `storage`, `artifactregistry`; Sessions, Memory Bank, Code Execution, eval are VPC-SC supported, Example Store is not |
| Cloud Run | Org policies `run.allowedIngress`, `run.allowedVPCEgress`; Direct VPC egress or connector with `all-traffic`; Private Google Access; IAM-principal ingress rules unsupported |
| Google APIs | Restricted VIP via PSC endpoint `--target-google-apis-bundle=vpc-sc` |

Telemetry: the variables that keep message content off ADK's spans are in
`SKILL.md`, default 5. What deployment adds: `--trace_to_cloud` is deprecated
on `adk deploy agent_engine`; use `--otel_to_cloud`, which sets the span
variable to `false` itself. Google Cloud Observability also recommends
`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=EVENT_ONLY` (content on log
records — approved sink only) and
`OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`.
`ADK_TELEMETRY_IGNORE_RUN_CONFIG` is in the 2.11 source/repo guide, not adk.dev.

## Perimeter (VPC-SC, no public egress) checklist

- Install from the internal PyPI mirror; pin with the repo's
  `constraints-3.x.txt`; install only needed extras (`[db]`, `[mcp]`, `[a2a]`,
  `[gcp]`, `[eval]`).
- Base image from the internal registry; build with your own Dockerfile rather
  than `adk deploy` if Cloud Build or public registries are unreachable.
- Vertex AI via ADC / Workload Identity, no API keys (variables:
  `app-and-services.md`, Models).
- Telemetry: content capture off (`SKILL.md`, default 5) unless the trace sink
  is approved for customer data.
- Durable sessions (`SKILL.md`, default 4) in-perimeter: Cloud SQL Postgres via
  `postgresql+asyncpg://...` or Agent Engine.
- Tool hygiene: `tool_filter` allow-lists, `require_confirmation=True` on
  state-changing tools, a policy plugin on the `App`.
- Idempotent nodes (`adk-workflows` rule 12); `max_llm_calls` as a loop/cost
  guard; `abort_signal` wired to client disconnects (built in for `/run_sse`
  since 2.11).
- Share agents across teams via A2A (`to_a2a`, `[a2a]` extra) or MCP
  (`to_mcp_server`) rather than code copies.
