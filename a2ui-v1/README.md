# A2UI demo: ADK agents → A2UI → React

A small learning prototype. ADK agents answer with A2UI surfaces, which travel as JSON
events over our own SSE endpoint and render with `@a2ui/react`. No A2A anywhere.

```
catalog/     shared A2UI catalog (custom components), used by backend and frontend
backend/     FastAPI + google-adk agents (uv project)
frontend/    React + TypeScript + Vite
```

## Pinned versions

| Package | Version |
|---|---|
| `a2ui-agent-sdk` (+ `a2ui-core`) | 0.6.0 (0.1.1) |
| `google-adk` | 2.9.2 |
| `@a2ui/react` | 0.11.1 |
| `@a2ui/web_core` | 0.11.0 |
| A2UI protocol | v0.9 (`DirectJsonFormat("0.9")` ↔ `@a2ui/react/v0_9`) |

Model: `gemini-3.1-flash-lite` on Vertex AI (set with `A2UI_DEMO_MODEL`).

## Run

Uses Vertex AI with Application Default Credentials:

```bash
gcloud auth application-default login
```

```bash
cp .env.example .env
```

Then set `GOOGLE_CLOUD_PROJECT` in `.env` (in `a2ui-v1/`, gitignored) to your Google Cloud project.

Backend (http://localhost:8080):

```bash
cd backend && uv run uvicorn app.api:app --reload --port 8080
```

Frontend (http://localhost:5173, proxies `/api` to the backend):

```bash
cd frontend && npm install && npm run dev
```

Then choose `weather_ui` and type "weather in Prague". Click **Refresh** on the card:
the agent fetches the weather again and the card updates in place ("updated HH:MM:SS").
The **Prague / Brno / London** buttons above the card do the same for another city: each
sends a `show_city` action with the city in its context, and the card switches to it. Every
action you send is listed under the surface ("↑ sent action …").

## Debugging agents with `adk web`

The ADK dev UI runs on its default port 8000 (the backend uses 8080, so both can run at
once):

```bash
cd backend/src/app/agents && uv run adk web
```

It talks to the agents directly, so you see the raw model output (including the
`<a2ui-json>` block) and tool calls, but not our validation, data binding, or SSE events.

## API

- `GET /api/agents` → `[{name, description, renders_a2ui}]`
- `POST /api/chat` `{agent, session_id?, text, action?}` → SSE with one JSON event per
  `data:` line: `progress` (tool call), `a2ui` (validated messages), `text`, `error` (safe
  message), and always `done` last with the `session_id`. `action` is an A2UI v0.9 user
  action from a rendered surface (e.g. the WeatherCard Refresh button).

## How the weather answer is built

1. The model calls `get_weather` (Open-Meteo), then writes **layout only**: `createSurface`
   and `updateComponents`, with every value bound to a data-model path.
2. The backend parses and validates the layout with the A2UI SDK against the merged catalog,
   enforces the component allow-list, and rejects any literal digit in component props.
3. The backend appends `updateDataModel` with the exact `get_weather` result. Invalid A2UI
   becomes a text fallback, so raw model JSON is never forwarded.

## Catalog

`catalog/weather_catalog.json` defines the custom `WeatherCard` in A2UI catalog JSON Schema.
The backend merges it into the bundled basic catalog (`backend/src/app/weather_catalog.py`),
and the frontend derives the catalog id and Zod schema from the same file
(`frontend/src/catalog.tsx`). `catalog/examples/` holds validated few-shot examples.

## Wire types

The events are Pydantic models in `backend/src/app/events.py`. The TypeScript types in
`frontend/src/api/wire.ts` are generated from them:

```bash
cd frontend && npm run gen:types
```

## Tests

```bash
cd backend && uv run pytest -q
```
