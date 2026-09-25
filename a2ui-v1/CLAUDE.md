# CLAUDE.md

Learning prototype: ADK agents answer with A2UI surfaces that travel as JSON events over
our own SSE endpoint and render in React. Keep it small and readable. See `README.md` for
setup and `NOTES.md` for findings and design reasoning.

## Commands

```bash
cd backend && uv run uvicorn app.api:app --reload --port 8080   # API
cd backend && uv run pytest -q                                  # tests (no model calls)
cd backend/src/app/agents && uv run adk web                     # ADK dev UI on :8000
cd frontend && npm run dev                                      # UI on :5173, proxies /api → :8080
cd frontend && npx tsc -p . && npm run build                    # typecheck + build
cd frontend && npm run gen:types                                # regenerate wire types
```

Ports: 8000 `adk web`, 8080 backend (also Cloud Run's default `PORT`), 5173 Vite.

## Hard rules

- **No A2A.** Don't import `a2ui.a2a`, `a2ui.adk.a2a`, or `a2ui.adk.send_a2ui_to_client_toolset`
  (it imports the A2A part converter). `a2a-sdk` is installed only as a transitive dependency.
- **Verify APIs against installed source** (`backend/.venv`, `frontend/node_modules`), not
  memory. A2UI is pre-1.0 and ADK 2.x differs a lot from 1.x.
- **Pinned versions** must move together: `a2ui-agent-sdk==0.6.0`, `google-adk==2.9.2`,
  `@a2ui/react@0.11.1`, `@a2ui/web_core@0.11.0`. The protocol is **v0.9** on both sides
  (`DirectJsonFormat("0.9")` ↔ `@a2ui/react/v0_9`, messages carry `"version": "v0.9"`).
- **No raw HTML in the frontend.** No `dangerouslySetInnerHTML`, and don't provide
  `MarkdownContext`: without it the A2UI `Text` component renders plain text.
- **Never forward raw model JSON.** Anything that fails parsing/validation/checks becomes a
  `text` event with a fallback message.
- **The model writes layout, the backend writes data.** Components bind to data-model paths.
  `updateDataModel` comes only from tool results (`registry.py` → `data_model`). The digit
  check rejects any literal number in component props.
- Errors sent to the client are safe messages only; log details server-side.
- Model name comes from `A2UI_DEMO_MODEL`. Vertex AI settings live in `.env` in this folder (gitignored, template: `.env.example`).

## Layout

```
catalog/weather_catalog.json   custom components (WeatherCard) + catalogId: single source of truth
catalog/examples/*.json        few-shot layouts, validated against the catalog when the prompt is built
backend/src/app/
  events.py                    Pydantic wire types (SSE events, ChatRequest); TS is generated from these
  api.py                       GET /api/agents, POST /api/chat (SSE); ADK Runner + InMemorySessionService
  registry.py                  agent name → root_agent, A2uiSupport, data_model builder
  a2ui_support.py              prompt generation, parse/validate, allow-list, digit check
  weather_catalog.py           merges catalog/*.json into the bundled basic catalog
  agents/<name>/agent.py       one folder per agent exposing `root_agent` (also what `adk web` loads)
frontend/src/
  api/wire.ts                  GENERATED, don't edit by hand
  catalog.tsx                  merged React catalog; Zod schemas derived from the catalog JSON
  a2ui.ts, A2uiView.tsx        MessageProcessor per assistant turn, surface rendering
  App.tsx                      agent picker, chat, SSE handling, action round trip
```

## Gotchas

- `A2uiSchemaManager` / `generate_system_prompt` are deprecated in SDK 0.6.0; use
  `DirectJsonFormat` and `format.prompt_generator.generate(...)`.
- `allowed_components` only prunes the prompt. The SDK validates against the full catalog,
  so the allow-list is enforced in `A2uiSupport.parse`.
- Pass A2UI prompts to `LlmAgent` as a callable (`instruction=lambda ctx: ...`) so ADK's
  `{state}` templating doesn't touch the embedded JSON schema.
- Digit check exemptions (ids, child refs, `{"path"}`, plain `${path}` interpolations, catalog
  enum props like `variant: "h3"`) are deliberate. Don't exempt function expressions: the
  model has hidden arithmetic in `${formatNumber(...)}`.
- React StrictMode runs state updaters twice. Keep side effects (processing A2UI messages)
  out of `setState` updaters; processors live in a ref.
- In this Chromium, `scrollIntoView` returns a Promise. Use a block body in `useEffect`,
  never an arrow that returns the call.
- `adk web` writes `.adk/` session folders next to each agent; they're gitignored.

## Changing things

- **Wire types:** edit `backend/src/app/events.py`, then `npm run gen:types`.
- **Custom component:** add it to `catalog/weather_catalog.json`, implement the render in
  `frontend/src/catalog.tsx` (startup fails if an implementation is missing), add it to the
  agent's `allowed_components`, and update the examples.
- **New agent:** create `agents/<name>/agent.py` with `root_agent` and register it in
  `registry.py`. For A2UI agents, give it an `A2uiSupport` and a `data_model` builder that
  only reads tool results.
- After backend changes run `uv run pytest -q`; after frontend changes run `npx tsc -p .`.
