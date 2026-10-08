# A2UI in ADK 2.x apps: developer guide

Research pass of 2026-10-02. Baseline: `google-adk` 2.10.0 (2.0 GA on 2026-05-19, roughly
bi-weekly releases), `a2ui-agent-sdk` 0.7.0 (2026-09-28, breaking), protocol v0.9.1 (current;
v1.0 is a candidate aimed at Q4 2026). Imports, signatures, schema files and the catalog id were
then checked on 2026-10-02 against `a2ui-agent-sdk` 0.7.0, `google-adk` 2.10.0, `a2a-sdk` 0.3.26,
the npm packages at 0.12.0 and the spec files at `python/a2ui-agent-sdk/v0.7.0` (commit `ec12ba9`).
Statements about behaviour that needs a model or a browser come from docs and issues.

## 1. The protocol in one page (v0.9.1)

A2UI is declarative and bound to a catalog: the agent sends JSON naming components from a
catalog the client already trusts, and the client renders its own widgets. No code is executed.
Apache-2.0, `github.com/a2ui-project/a2ui` (old `google/A2UI` links redirect), still "early stage
public preview".

| Concept | Meaning | Note |
|---|---|---|
| Surface | A canvas with a `surfaceId` | Many per session, each with its own data model |
| Catalog | JSON Schema of allowed components and functions | Basic catalog: 18 components |
| Components | Flat list `{"id","component","child"/"children",...}`, root id `root` | Children by id, so it streams |
| Data model | Per-surface JSON; props bind with `{"path": "/a/b"}` | Inputs write locally; server sends `updateDataModel` |
| Actions | `event` (to the agent) or `functionCall` (runs on the client, e.g. `openUrl`) | Context values may be paths resolved at click time |
| Checks | Client-side conditions such as `required` | UX only; the agent must validate again |
| Data model sync | `createSurface.sendDataModel: true` sends the whole model with every message | Data-exposure risk; keep off |
| Errors | Client may send `error` with `code: VALIDATION_FAILED` | Feed back to the model as `[UI_ERROR]` |

Basic catalog: Row, Column, List, Card, Tabs, Modal, Text, Icon, Divider, Image, Video,
AudioPlayer, Button, TextField, CheckBox, ChoicePicker, Slider, DateTimeInput. Functions include
`required`, `email`, `formatString`.

Versions: v0.8 used `beginRendering/surfaceUpdate/dataModelUpdate/deleteSurface` + `userAction`;
v0.9 and v0.9.1 use `createSurface/updateComponents/updateDataModel/deleteSurface` + `action`;
v1.0 (candidate) adds `actionResponse` and action ids and renames `theme` to `surfaceProperties`.
As of 2026-09-29 (a2ui #2873) no web renderer has v1.0 adapters.

Server to client, one object per message:

```json
{"version":"v0.9.1","createSurface":{"surfaceId":"intake","catalogId":"<BASIC_CATALOG_ID>","sendDataModel":false}}
{"version":"v0.9.1","updateComponents":{"surfaceId":"intake","components":[
  {"id":"root","component":"Card","child":"col"},
  {"id":"col","component":"Column","children":["title","amount","submit"]},
  {"id":"title","component":"Text","text":"Overdraft limit request"},
  {"id":"amount","component":"TextField","label":"Requested limit (EUR)","value":{"path":"/form/amount"}},
  {"id":"submit","component":"Button","child":"submit_lbl",
   "action":{"event":{"name":"submit_limit_request","context":{"amount":{"path":"/form/amount"}}}}},
  {"id":"submit_lbl","component":"Text","text":"Submit"}]}}
{"version":"v0.9.1","updateDataModel":{"surfaceId":"intake","path":"/form","value":{"amount":""}}}
```

Client to server:

```json
{"version":"v0.9.1","action":{"name":"submit_limit_request","surfaceId":"intake",
 "sourceComponentId":"submit","timestamp":"2026-10-02T10:00:00Z","context":{"amount":"5000"}}}
```

Catalog id: the basic catalog for v0.9 **and** v0.9.1 is
`https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json` - the v0.9.1 spec files keep
their `v0_9` `$id`s, and SDK 0.7.0 reports the same id (`DirectJsonFormat("0.9.1",
...).supported_catalog_ids`). The older `.../v0_9/basic_catalog.json` alias returns 404; ids with
`v0_9_1` seen in some examples are not what the SDK or the schema use.

## 2. What ADK 2.0 changes for A2UI

| Change | Consequence |
|---|---|
| Workflow runtime: `BaseAgent` is a `BaseNode`; `Workflow(edges=...)`, `@node`, `RequestInput` | A form becomes a node that yields `RequestInput`; the action's context resumes it. `_run_async_impl` overrides are bypassed. |
| Event schema adds `node_info`, `output` | Store events as JSON; strict client validators with `additionalProperties: false` break |
| No `session.events.append`, no `enqueue_event` | A2UI travels in tool results, callbacks or yielded events |
| Framework retries and HITL interrupts | No broad `except` in tools (masks failures, can swallow `NodeInterruptedError`) |
| `Context.render_ui_widget(UiWidget)` (since 1.27) | Fine for `adk web`/own hosts; not converted to A2A as of 2.11.0 (adk-python #7308) |
| A2A with `a2a-sdk` 0.3.x and 1.x; `to_a2a()`, `adk api_server --a2a`, `A2aAgentExecutorConfig(event_converter=...)` | The hook for the SDK's `A2uiEventConverter` |
| 2.0 sessions readable by 1.28+ only | Pin the same version across services sharing a session DB |

## 3. Routes

| | How | For | Against |
|---|---|---|---|
| **SSE** (default) | Tools return validated A2UI; FastAPI streams it; client runs `@a2ui/web_core` | Full control, auditable, no dependence on ADK/A2A gaps, works behind VPC-SC | ~150 lines of transport you own |
| **A2A** + extension | Agent card advertises `https://a2ui.org/a2a-extension/a2ui/v0.9.1`; client sends `a2uiClientCapabilities` | Gemini Enterprise and other A2A clients, multi-agent (`A2uiSubagentMap`) | Payload shape and MIME disagreements, #7308, more moving parts |
| **Tagged text** (`<a2ui-json>`) | Model writes JSON in text; SDK `parse_response` | Prototypes; what a2ui-surfaces and `adk web` use | Parsing is fragile; no tool-level self-correction |

Tagged text and SSE are not exclusive: a2ui-surfaces parses tagged text in the verify node;
`emit_ui` is the same idea as a tool, so the model gets validation errors back in the same turn.
(The adk-architecture shell is its Pattern A; these routes are a separate choice.)

```
Browser (vendored Lit/React)            FastAPI on Cloud Run (IAP/OIDC)          ADK Runner
 POST /api/chat {text}        ───────►  /api/chat   ── run_async ──────────►   agent / workflow nodes
 POST /api/action {action}    ───────►  /api/action ── validate, own, route ─►  show_* | emit_ui | data tools
 SSE {"type":"a2ui"|"text"}   ◄───────  to_sse(event)                           Vertex AI Gemini via PSC
 MessageProcessor → <a2ui-surface>
```

## 4. The SSE route step by step

### 4.1 Setup

```toml
[project]
requires-python = ">=3.11,<3.14"
dependencies = [
  "google-adk[a2a,db]==2.10.0",     # db: DatabaseSessionService needs sqlalchemy
  "a2ui-agent-sdk==0.7.0",          # only imported under app/a2ui/
  "a2ui-core>=0.2.0,<0.3.0",
  "a2a-sdk[http-server]>=0.3.4,<0.4",  # the SDK caps a2a-sdk below 0.4, ADK allows <2
  "jsonschema>=4.23,<5",
  "fastapi", "uvicorn[standard]",   # pin exact versions in the lock
]
```

Install from the Nexus mirror with a lock (`uv lock`, `uv pip sync --require-hashes`). Vendor
`specification/v0_9_1/json/{server_to_client,client_to_server,common_types}.json` and
`specification/v0_9_1/catalogs/basic/catalog.json` into `schemas/a2ui/v0_9_1/` with a README naming
the commit. There is no `v0.9.1` tag; `python/a2ui-agent-sdk/v0.7.0` is the matching release tag. Model access through ADC:

```bash
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT=<project>
GOOGLE_CLOUD_LOCATION=<approved region>
```

The Next '26 codelab uses `GOOGLE_GENAI_USE_ENTERPRISE=True` with `location=global`; check which
flag your pinned `google-genai` honours. Pin a model version, not `*-latest`.

### 4.2 Validation and templates

[code/validator.py](code/validator.py): vendored schemas (Draft 2020-12 with a `referencing`
registry, no network), allow-lists for components and events, no `functionCall`, no
`sendDataModel`, child refs resolve, version pinned, and for model-written layout no
`updateDataModel`. `client_to_server.json` has no `$schema`, so resources are created as Draft
2020-12 explicitly; the catalog is also registered at the `catalog.json` slot that
`server_to_client.json` refers to. The digit check for model layout comes from a2ui-surfaces.
Optionally also run the SDK's strict check inside `app/a2ui/`:
`DirectJsonFormat("0.9.1", catalogs=[...]).get_selected_catalog().validate(msgs)` (a
`MessageProcessor` in strict mode; raises on dangling references and unknown components). In 0.7.0
`parser.parse_response` does not validate at all.

[code/templates.py](code/templates.py): one function per form. Templates are code, so they may
write the data model; they are golden-tested and validated with `model_written=False`.

### 4.3 Tools and instruction

[code/agent_tools.py](code/agent_tools.py). `show_limit_form` renders a template;
`emit_ui(layout_json)` validates model layout, then appends `updateDataModel` built from this
turn's tool results. Only JSON and validation errors are caught; anything else raises so ADK's
retries work. Optionally append the SDK prompt (schema plus validated examples) from
a2ui-surfaces: `DirectJsonFormat(version, catalogs=[...]).prompt_generator.generate(...)` with
`allowed_messages=["CreateSurfaceMessage", "UpdateComponentsMessage"]` (0.7.0 signature:
`role_description, workflow_description, ui_description, client_ui_capabilities,
allowed_components, allowed_messages, include_schema, include_examples, validate_examples`).

### 4.4 Actions

[code/actions.py](code/actions.py). Order: schema, allow-list, size cap → the surface belongs to
this session → transactional actions run in code (pydantic, entitlements) and only their result
reaches the model as `[UI_ACTION_RESULT]` → other actions reach the model as `[UI_ACTION]` data.
With a Workflow, the form node yields `RequestInput(message=..., response_schema=Model)` and the
action context is the resume payload: a `FunctionResponse` named `adk_request_input` whose `id`
is the request's `interrupt_id`. ADK validates and coerces the answer against `response_schema`
(`'500'` → `500`). An invalid answer raises `WorkflowDataError` out of `run_async`, and that
interrupt then keeps failing in the session, even for a later valid answer - so validate the
context against the same Pydantic model first and send errors back to the form without calling the
runner (`actions.py`). Verified on `google-adk` 2.11.0. The app needs
`App(..., resumability_config=ResumabilityConfig(is_resumable=True))` (EXPERIMENTAL warning in
2.11).

### 4.5 Transport

[code/server.py](code/server.py). `to_sse` turns function responses with `status == "rendered"`
into `{"type":"a2ui","messages":[...]}` and final non-thought text into `{"type":"text"}`. The
runner is built from `App` (`Runner(app=..., session_service=...)`), so plugins and resumability are
available. ADK's built-in `/run_sse` cancels the run on client disconnect via `abort_signal`
(release notes v2.11.0); own routes don't get that for free, so both routes pass
`abort_signal=asyncio.Event()` and set it when `await request.is_disconnected()`. The
client bundle is served from the same service, so no CORS.

### 4.6 Streaming, updates, several surfaces

- Send `createSurface` and `updateComponents` first, `updateDataModel` when data arrives;
  re-sending only `updateDataModel` refreshes values without rebuilding the tree. An action turn
  upserts only the keys it produced (a2ui-surfaces).
- Token streaming of model layout: `DirectJsonStreamParser(catalog=...).process_chunk(text)` exists,
  but 0.7.0 has v0.9.1 bugs (a2ui #2935 relative paths become absolute, so List template rows render
  empty; #2936 partial `updateDataModel` loses its path and wipes the model). Buffer and validate
  whole payloads.
- Stable semantic surface ids (`limit_form`, `findings`, `history`), tracked in
  `state["ui:surfaces"]` (an ordinary session-scoped key: only `app:`, `user:` and `temp:` are
  special; verified 2.11.0), `deleteSurface` when a flow ends. In multi-agent setups route surface
  data only to the owning sub-agent and strip `a2uiClientDataModel` from other requests.

### 4.7 The A2A route

[code/a2a_main.py](code/a2a_main.py). The agent card advertises the extension with
`supportedCatalogIds` and `acceptsInlineCatalogs: false` (clients must not push schemas into your
prompt): `a2ui.a2a.extension.get_a2ui_agent_extension("0.9.1", supported_catalog_ids=[...])`. The client negotiates with header `X-A2A-Extensions:
https://a2ui.org/a2a-extension/a2ui/v0.9.1` and sends `a2uiClientCapabilities:
{"v0.9.1": {"supportedCatalogIds": [...]}}` in message metadata;
`a2ui.a2a.extension.try_activate_a2ui_extension(context, agent_card)` returns the negotiated
version. The SDK's `A2uiEventConverter` reads the catalog from `state["system:a2ui_catalog"]`;
nothing in the SDK writes that key, so that is the app's job if you use it.

Outgoing parts: `to_a2a`'s default converter ignores A2UI (#7308). In SDK 0.7.0 the ready-made
`A2uiEventConverter` is a poor fit: it plugs into `A2aAgentExecutorConfig.event_converter`, which
only ADK's legacy executor path uses (the new path uses `adk_event_converter`); it only converts
`send_a2ui_json_to_client` results (or every tool with `bypass_tool_check=True`); and it builds its
part converter with version `"0.8"`, so parts carry the deprecated MIME. `a2a_main.py` instead
passes a `gen_ai_part_converter`, used by both paths (`to_a2a(..., agent_executor_factory=...)` and
`A2aAgentExecutorConfig(gen_ai_part_converter=...)` re-verified on 2.11.0 with `a2a-sdk` 0.3.26;
`google.adk.a2a` still has no A2UI conversion there), that maps `status == "rendered"` responses to
`create_a2ui_part(msg, version="0.9.1")`. Shape: the v0.9.1 extension text says the DataPart `data`
must be an array; `create_a2ui_part` and the Flutter `genui_a2a` client use one message per part
with `metadata.mimeType`. One per part is what works today. The SDK hard-depends on `a2a-sdk`
(`>=0.3,<0.4`) even on the SSE route.

## 5. Client

| Renderer | Package | v0.9 | Note |
|---|---|---|---|
| Lit | `@a2ui/lit` + `@a2ui/web_core` | stable | Lightest; embeds in an existing portal |
| React | `@a2ui/react` + `@a2ui/web_core` | stable | `A2uiSurface` from `@a2ui/react/v0_9`; custom components in a2ui-surfaces |
| Angular | `@a2ui/angular` + `@a2ui/web_core` | stable | `CatalogComponent`, `AngularCatalog(...)` |
| Flutter | `genui`, `genui_a2a` | yes | One message per DataPart |
| Compose | `androidx.a2ui` 1.0.0-alpha01 | alpha | |
| `adk web` | built in | v0.8 only | Dev only |

[code/main.ts](code/main.ts) is a minimal Lit client. Keep `functionCall` handling off (a2ui #2837:
`web_core` currently dispatches it as an `onAction` event, behaviour in flux). Self-host Material
Symbols for `Icon`.

## 6. Custom catalogs

1. Catalog JSON Schema with its own id, e.g. `https://bank.internal/a2ui/v0.9/bank_catalog_v1.json`
   (ids only need to be unique). Self-contained, because basic components `$ref` the catalog's own
   `$defs` (a2ui-surfaces).
2. Client implementation registered in the `MessageProcessor` next to `basicCatalog`.
3. Server: `CatalogConfig.from_path(name=..., catalog_path=..., examples_path=...)` and the
   validator's allow-list.
4. Negotiation as in §4.7; the agent stamps the chosen id into `createSurface.catalogId`.

## 7. Tests, eval, fallbacks

- pytest: every template validates; golden snapshots; negative cases (unknown component, unknown
  event, dangling child, `functionCall`, model `updateDataModel`, digits); action rejections.
- Contract: the same goldens through `MessageProcessor` in vitest, against the vendored schema.
- ADK eval: `tool_trajectory_avg_score`, `final_response_match_v2` or rubrics, `hallucinations_v1`,
  and a custom metric for the share of valid `emit_ui` calls per model version.
- Debugging: A2UI Composer and Theater are hosted - synthetic data only, outside the perimeter.
  Log validator errors with surface id and a payload hash.
- Fallbacks: tool errors back to the model (two corrections, inside one agent run) → plain text → client catch with a
  neutral message → for critical flows a template always exists.

## 8. Production in a restricted environment

Supply chain: Python and npm pinned with hashes from Nexus; client built in CI and shipped inside
the container image (base from Quay); SBOM and vulnerability scan; watch `@a2ui/web_core`
advisories (a2ui #2385, CWE-209: full V8 stack traces reach `onError` subscribers in 0.10.6).

Model: Vertex AI via Private Google Access/PSC inside the perimeter, ADC from the service account
(`roles/aiplatform.user` only), approved region, pinned model, modest `HttpRetryOptions`.

Auth: IAP or the bank's OIDC in front of Cloud Run, JWT verified in FastAPI, `user_id` from the
verified subject, sessions bound to the user; A2A calls with service-account ID tokens and
audience checks.

Security review:

1. **Injection through actions**: context, free text and synced data models are user data.
   Schema, allow-list, size cap, `[UI_ACTION]` framing, instruction rule, deterministic
   transactions, server-side authorisation; client checks are UX only.
2. **Misleading UI**: the catalog stops code, not lies - a fake "Approved" card, or an `Image`
   URL used as a beacon. Drop `Image`/`Video` or allow one origin (CSP `img-src 'self'`), disable
   `functionCall`, templates for anything with legal meaning.
3. **Data exposure**: `sendDataModel` off; no more PII in a data model than the user may see;
   mask account numbers in tools; session DB classified for what it stores.
4. **Multi-agent leakage**: surface data only to its owner.
5. **Logging**: redact before Cloud Logging; validator messages carry no values.

Deploy: own image (FastAPI plus `web/dist`), `gcloud run deploy --no-allow-unauthenticated
--ingress internal-and-cloud-load-balancing`, secrets from Secret Manager. Agent Runtime
(formerly Vertex AI Agent Engine, part of Gemini Enterprise Agent Platform; the CLI is still
`adk deploy agent_engine`) hosts the agent but not the UI or SSE BFF - pair it with a Cloud Run
BFF or use the A2A route. Sessions: `DatabaseSessionService` on Cloud SQL (JSON event columns) or
`VertexAiSessionService`. Networking rules for Agent Runtime and Cloud Run inside a perimeter
(PSC-I, VPC-SC): [adk-app-runtime deployment](../../adk-app-runtime/references/deployment.md#official-networking-rules-docscloudgooglecom-checked-2026-10-02).

## 9. Maturity (2026-10)

| Area | State |
|---|---|
| Spec | v0.9.1 current, v1.0 candidate, public preview |
| Python SDK | 0.7.0 breaking; `parse_response` no longer validates; docs behind; stream parser bugs #2935, #2936 |
| ADK ↔ A2A ↔ A2UI | #7308 open (2.11.0); adk.dev shows old MIME; SDK converter is legacy-path only |
| `adk web` | v0.8 renderer |
| Wire shape | array vs one message per DataPart |
| Renderers | no v1.0 adapters; `functionCall` in flux (#2837) |
| Security | #2385 stack traces in `onError` |

## Sources

- a2ui.org: home, concepts (overview, actions), specification v0.9.1 and v0.9, A2A extension
  v0.9.1, roadmap, guides (agent development, any agent framework, authoring components)
- Installed packages (2026-10-02): `a2ui-agent-sdk` 0.7.0, `a2ui-core` 0.2.0, `google-adk` 2.10.0,
  `a2a-sdk` 0.3.26; npm `@a2ui/web_core`, `@a2ui/lit` 0.12.0
- github.com/a2ui-project/a2ui: README, `specification/v0_9_1` at tag `python/a2ui-agent-sdk/v0.7.0`, issues #2385,
  #2837, #2873, #2935, #2936
- github.com/google/adk-python: README, issue #7308; pypi.org/project/google-adk
- adk.dev: 2.0, graphs (dynamic, human input), integrations/a2ui, evaluate/criteria
- codelabs.developers.google.com/next26/adk-a2ui (Next '26 codelab)
- developers.googleblog.com/a2ui-v0-9-generative-ui
- npmjs.com/package/@a2ui/lit; developer.android.com/jetpack/androidx/releases/a2ui
