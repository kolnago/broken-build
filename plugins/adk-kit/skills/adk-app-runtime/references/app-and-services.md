# App, Runner and services (ADK 2.x)

## App fields

`name`, `root_agent` (an agent or any `BaseNode`, incl. `Workflow`),
`plugins`, `resumability_config=ResumabilityConfig(is_resumable=True)`,
`context_cache_config`, `events_compaction_config`. The CLI loader looks for a
module-level `app` first, then `root_agent`, and warns if `app.name` differs
from the folder name.

## Runner

`Runner(app=app, session_service=..., artifact_service=..., memory_service=...)`;
`InMemoryRunner(app=app)` for tests. `run_async(user_id, session_id,
new_message, run_config=None, state_delta=None, abort_signal=None)`.
Passing both `app` and `plugins` raises.

## State scopes

| Key | Persisted | Visible to |
|---|---|---|
| `k` | yes | this session |
| `user:k` | yes | this user, all sessions of the app |
| `app:k` | yes | all users and sessions of the app |
| `temp:k` | no | this invocation |

Read prefixed keys with the prefix (`{user:home_city?}`). `State` has no
iteration/`del`; use `to_dict()`. `None` is stored, not deleted. `temp:` keys
in `create_session(state=...)` are dropped. No atomic read-modify-write.
`state_schema` skips keys containing `:`. `VertexAiSessionService` does not
split scopes.

## Services and URIs (CLI flags / get_fast_api_app args)

| Service | Built-in URI schemes | Classes |
|---|---|---|
| Session (Agent Runtime = formerly Vertex AI Agent Engine) | `memory://`, `sqlite:///path.db`, `postgresql://`, `mysql://`, `agentengine://<id>`; other SQLAlchemy URLs (e.g. `postgresql+asyncpg://`) fall back to `DatabaseSessionService` | `InMemorySessionService`, `SqliteSessionService` (`google.adk.sessions.sqlite_session_service`), `DatabaseSessionService` (`[db]`), `VertexAiSessionService`; Firestore, Redis integrations |
| Artifact | `memory://`, `file://`, `gs://bucket` | `InMemoryArtifactService`, `GcsArtifactService` |
| Memory | `memory://`, `sqlite://` (2.11), `agentengine://<id>`, `rag://<corpus>` | `InMemoryMemoryService` (keyword match), `VertexAiMemoryBankService` (semantic), `VertexAiRagMemoryService` |

Custom backends: register a scheme with the `ServiceRegistry`
(`services.yaml` / `services.py` in the agents dir).
Upgrading a 1.x session DB: `adk migrate session`.

## Memory use

Tools `load_memory` / `preload_memory`, or `await ctx.search_memory(query)`.
Ingest finished sessions with `memory_service.add_session_to_memory(session)`.

## Artifacts

`await ctx.save_artifact('report.pdf', types.Part.from_bytes(data=b, mime_type='application/pdf'))`
returns a version; `await ctx.load_artifact('report.pdf')`. Namespaced by app
since 2.6.

## Models

Pin `model=` (why and which name: `adk-workflows`, Project layout); the built-in default can be changed with `LlmAgent.set_default_model` or `--default_llm_model`. `FallbackModel(models=[...])` for
failover (experimental, 2.9). Non-Gemini: `LiteLlm`, Anthropic, OpenAI extra.
Vertex: `GOOGLE_GENAI_USE_ENTERPRISE=TRUE` + project/location (ADC).
