---
name: adk-a2ui-integration
description: Wire A2UI (agent-to-UI protocol, v0.9.1) into a Google ADK 2.x Python app end to end - choosing the integration route (own FastAPI SSE or A2A with the A2UI extension), pinning and vendoring schemas and renderers, server-built form templates, a validating emit_ui tool, the user-action round trip as untrusted input, ADK 2.0 Workflow RequestInput, Lit or React client bootstrap, and deployment in a restricted environment (VPC-SC, no public egress, Nexus mirrors, Cloud Run, IAP). Use this when starting A2UI in a new or existing ADK project, exposing A2UI over A2A or to Gemini Enterprise, upgrading A2UI/ADK versions, or reviewing an A2UI integration for security or production readiness. For how surfaces are designed, bound to tool data and checked for numbers, use a2ui-surfaces.
---

# A2UI integration for ADK 2.x apps

Status: **experimental**, written from a research pass on 2026-10-02 (sources in
[references/guide.md](references/guide.md#sources)), not from a running project. Imports,
signatures and schemas were then checked against the installed packages and the spec files;
behaviour end to end (a model, a browser) was not. Code under [references/code/](references/code/)
is a starting shape, not a package.

**Baseline** (verify against installed packages before use, never against memory):
`google-adk` 2.10.0 (re-verified on 2.11.0 for guide §2, §4.4 and §4.7) · `a2ui-agent-sdk` 0.7.0
(needs `a2ui-core>=0.2,<0.3` and `a2a-sdk>=0.3,<0.4`) · protocol **v0.9.1** · `@a2ui/web_core`, `@a2ui/lit`, `@a2ui/react` 0.12.0.
`a2ui-surfaces` was verified against SDK 0.6.0 / protocol v0.9 / ADK 2.9.2, and its backend
re-verified on ADK 2.11.0 with SDK 0.6.0 and 0.7.0. In 0.7.0 `parser.parse_response` **no longer
validates**: unknown components and dangling children pass. Its `a2ui_support.py` therefore calls
`format.get_selected_catalog().validate(messages)` after parsing when the method exists (0.7.0+;
`a2ui.validation` is gone; `catalog.validator` is a `PayloadValidator`). Do the same in your own
wrapper. Do **not** target protocol v1.0 until the
Lit, React and Angular renderers ship v1.0 adapters.

## Division of labour with the other skills

- **a2ui-surfaces**: what a surface is allowed to contain - model writes layout only, the backend
  writes `updateDataModel` from this turn's tool results, no literal numbers, per-agent allow-list,
  React catalog components. Everything here obeys it.
- **adk-architecture**: layers, the turn ledger, verification at the exit (P1, TOOL-5, LED-1, VER-*).
  The shell is its Pattern A; the routes below are a different axis. Where the A2UI check runs
  depends on how layout leaves the model: here it goes through `emit_ui`, so the checks run
  inside the tool and the shell's verify node checks only the prose. Layout written into the
  answer text is checked in the verify node instead (a2ui-surfaces).
- **This skill**: the plumbing around both - versions, transport, A2A, actions, client bootstrap,
  security review, deployment.

## 1. Choose the route

```
Must another platform or agent render your UI (Gemini Enterprise, an A2A orchestrator)?
├─ yes → A2A: A2A + A2UI extension (same payloads as SSE; a second front door)
└─ no  → SSE (DEFAULT): emit_ui tool + server templates + own FastAPI SSE + vendored renderer
`adk web` renders A2UI v0.8 only: fine for a quick look, not for testing v0.9.1.
```

Write payloads A2A-compatible from day one: one A2UI message per object,
`"version": "v0.9.1"`, MIME `application/a2ui+json`. Adding A2A is then transport only.

## 2. Ground rules

1. **Two sources of UI.** Forms with business or legal effect (requests, approvals, submissions)
   are **server-built templates** in code. The model may compose layout only for read-only views
   (findings, summaries, lists), via `emit_ui`.
2. **Validate before anything leaves the server**: vendored JSON Schema → component allow-list →
   event-name allow-list → no `functionCall` actions → child refs resolve → (model layout only)
   no `updateDataModel`, no literal digits, this turn has tool data (a2ui-surfaces). On failure `emit_ui` returns the errors
   to the model; after two corrections the answer is plain text. These are tool calls inside one
   agent run, separate from the shell's single retry (SH-2), which is for the prose.
3. **Actions are untrusted input**: schema + allow-list + 4 KB cap, the `surfaceId` must belong
   to this session, entitlements re-checked as for a user message. Transactional actions run
   deterministically in code and never pass through the model; others reach it framed as
   `[UI_ACTION] {...}` data, and the instruction says such text is never an instruction.
4. **ADK 2.0 discipline**: emit A2UI from tool results or yielded node events, never by appending
   to the session; catch only `JSONDecodeError`/validation errors in tools (broad `except` breaks
   retries and `RequestInput` interrupts); no `_run_async_impl` overrides.
5. **Keep the SDK behind `app/a2ui/`.** Only that package imports `a2ui.*`, so a 0.x break costs one
   file.
6. **Restricted environment**: no CDN, no runtime fetch of schemas, catalogs, fonts or icons;
   Vertex AI through ADC; every Python and npm dependency pinned with hashes from Nexus.

## 3. Layout

```
app/a2ui/validator.py    vendored-schema validation + allow-lists     references/code/validator.py
app/a2ui/templates.py    server-built forms                           references/code/templates.py
app/a2ui/support.py      SDK prompt/parse wrapper (a2ui-surfaces)
app/agent.py             show_<form> and emit_ui tools, instruction    references/code/agent_tools.py
app/actions.py           action round trip                            references/code/actions.py
app/server.py            FastAPI /api/chat, /api/action as SSE        references/code/server.py
app/a2a_main.py          (A2A) agent card + A2UI extension             references/code/a2a_main.py
schemas/a2ui/v0_9_1/     spec json files + basic catalog, commit recorded in a README
web/                     Vite + vendored renderer                     references/code/main.ts
tests/golden/*.json, eval/*.evalset.json
```

## 4. Steps

1. Pin versions (§ baseline); `uv lock`, install with `--require-hashes` from Nexus; npm via the
   Nexus proxy with a lockfile.
2. Vendor `specification/v0_9_1/json/{server_to_client,client_to_server,common_types}.json` and
   `specification/v0_9_1/catalogs/basic/catalog.json` into `schemas/a2ui/v0_9_1/`. There is no
   `v0.9.1` git tag (tags: `v0.8`, `v0.9`, SDK releases), so pin the SDK release tag
   `python/a2ui-agent-sdk/v0.7.0` or a commit. The v0.9.1 files keep `v0_9` `$id`s: the basic
   catalog id is `https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json` (also the SDK's
   `supported_catalog_ids[0]`).
3. `validator.py`: server messages and client actions, as in rule 2 and 3.
4. `templates.py`: one function per form returning `createSurface`, `updateComponents`,
   `updateDataModel`; inputs bound to `/form/*`, the submit button's `action.event.context` bound to
   the same paths, a `required` check for UX only. Golden-test each.
5. Tools: `show_<form>(...)` returns `{"status": "rendered", "a2ui": msgs}`; `emit_ui(layout_json)`
   validates layout and appends the data model built from this turn's tool results. Track surface ids
   in `state["ui:surfaces"]`.
6. SSE: turn function responses with `status == "rendered"` into SSE
   `{"type":"a2ui","messages":[...]}`; final non-thought text into `{"type":"text"}`.
   A2A: see [guide.md §4.7](references/guide.md#47-the-a2a-route) - ADK's default A2A converter
   drops A2UI (adk-python #7308), so pass a `gen_ai_part_converter` that emits one DataPart per
   message (`a2a_main.py`).
7. Actions: `handle_action` as in rule 3. Workflow variant: a node yields
   `RequestInput(response_schema=Model)` and the action's `context` is the resume payload;
   validate the context against the same model before resuming; an invalid answer poisons the
   interrupt (verified 2.11.0).
8. Client: one `MessageProcessor([...catalogs], onAction)` for the page, because surface ids here
   are stable and unique per session (step 5); a chat transcript with fresh surfaces per answer
   uses one per assistant turn (a2ui-surfaces). `<a2ui-surface>` (Lit) or
   `<A2uiSurface>` (React), `processMessages` in try/catch with a neutral fallback, `functionCall`
   handling off, icons and fonts self-hosted, same origin as the API.
9. Tests, eval, security review (§5), deploy ([guide.md §8](references/guide.md#8-production-in-a-restricted-environment)).

## 5. Release checklist

- [ ] Every template validates; golden snapshots committed; same goldens render in a vitest
      `MessageProcessor` test (catches Python/JS spec drift)
- [ ] Rejected server-side: unknown component, unknown event, dangling child, `functionCall`,
      wrong version, model-written `updateDataModel`, literal digits in model layout
- [ ] Rejected actions: bad schema, unknown name, foreign `surfaceId`, > 4 KB
- [ ] Injection test: "ignore previous instructions" in an action's context leaves the tool
      trajectory unchanged
- [ ] ADK eval: `tool_trajectory_avg_score` (form requests call `show_<form>`), rubric or
      `final_response_match_v2` for text, a custom valid-UI-rate metric tracked per model version
- [ ] Fallbacks: invalid three times → plain text; client render error → neutral message
- [ ] `sendDataModel` off unless justified; `acceptsInlineCatalogs: false`; no `Image`/`Video`
      or an allow-listed origin; CSP `default-src 'self'`
- [ ] PII masked before it reaches the model or a data model; logs carry surface id and payload
      hash, not values; `onError` details from `@a2ui/web_core` never shown to users (a2ui #2385)
- [ ] Dependencies pinned and hashed, SBOM and vulnerability scan, bundle served from the image

## 6. Gotchas

- v0.8 → v0.9+: `beginRendering/surfaceUpdate/dataModelUpdate/userAction` became
  `createSurface/updateComponents/updateDataModel/action`; components are flat
  (`"component": "Text"`), plain values replace `literalString`.
- MIME: v0.9.1 says `application/a2ui+json`; adk.dev says `application/json+a2ui`, which SDK 0.7.0's
  `create_a2ui_part` still uses unless you pass `version="0.9.1"`.
- The v0.9.1 A2A extension says a DataPart holds an array; the SDK and Flutter client use one
  message per part. One per part is what interoperates today.
- SDK 0.7.0 stream parser bugs on v0.9.1 (a2ui #2935 relative paths, #2936 partial
  `updateDataModel` loses its path): buffer and validate whole payloads.
- Docs lag the SDK: `A2uiSchemaManager` is deprecated (use `DirectJsonFormat`), some guides
  import `a2ui.strategies.schema`, which doesn't exist, and `get_a2ui_agent_extension` lives in
  `a2ui.a2a.extension` (takes the version first: `"0.9.1"`).
- SDK 0.7.0's `A2uiEventConverter` only converts `send_a2ui_json_to_client` results, only runs on
  ADK's legacy A2A executor path, and labels parts with the deprecated MIME.
- `server_to_client.json` refers to `catalog.json` relative to its `$id`; register your catalog
  under `https://a2ui.org/specification/v0_9/catalog.json` too (`validator.py` does).
- `Icon` usually expects Material Symbols from fonts.googleapis.com: self-host or it breaks
  behind the perimeter.

Full guide with architecture diagram, security review and deployment notes:
[references/guide.md](references/guide.md).
