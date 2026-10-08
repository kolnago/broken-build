---
name: a2ui-surfaces
description: Let Google ADK agents answer with A2UI surfaces (interactive cards, lists, buttons, master-detail views) rendered in a React frontend, without A2A - backend prompt generation and validation with a2ui-agent-sdk, data bound from tool results, action round trips, custom catalog components, and the React renderer. Use this whenever an ADK agent should return UI instead of, or next to, prose - "generative UI", "the agent should show a card / list / form / buttons", "render the answer as a widget" - and whenever the user builds or debugs A2UI surfaces, catalogs, actions, data bindings or the React side, a surface fails validation, or the model writes numbers into a UI. For transport (SSE, A2A), version pins, action security, deployment and forms that submit something (server-built templates, not model layout), use adk-a2ui-integration.
---

# A2UI surfaces for ADK agents

Status: **experimental**, from one prototype (a2ui-v1). The decisions are argued in
[references/adr-a2ui-surfaces.md](references/adr-a2ui-surfaces.md); working code is in
[references/code/](references/code/).

**Verified against** `a2ui-agent-sdk==0.6.0`, `google-adk==2.9.2`, `@a2ui/react@0.11.1`,
`@a2ui/web_core@0.11.0`, protocol **v0.9** (the prototype: real model, real browser).
**Backend re-verified** on `google-adk==2.11.0` with `a2ui-agent-sdk` 0.6.0 and 0.7.0
(2026-10-02, offline with a scripted model): prompt generation, parsing, the allow-list and digit
checks, the custom-catalog merge, the callable instruction and the `api.py` event loop. Not
re-verified: the React side on newer `@a2ui/*` packages, behaviour with a real model, the cost
figures. A2UI is pre-1.0: pin these together and check APIs against the installed packages, not
memory.

## When to use it, and when not

Use it when the agent **decides what to show**: the view depends on the data or on judgement
(list vs detail vs warning), or buttons need judgement ("draft reminder", "explain"). If the
screen always looks the same, build ordinary UI and keep the LLM in prose or inside tools.
Buttons with a fixed meaning (select, refresh, page) are handled by code, not the model.

The model composes **read-only views**. A form whose submission has business or legal effect
(a request, an approval) is a server-built template in code, never model layout
(adk-a2ui-integration, ground rule 1). Input components in model-written layout are an open
question in the ADR; keep them off the allow-list until it is decided.

## The model

1. **The model writes layout, code writes data.** The model sends only `createSurface` and
   `updateComponents`; components bind to data paths (`{"path": "/selected/total"}`). The
   backend appends one `updateDataModel` built from **this turn's tool results** (the turn
   ledger). A model-written `updateDataModel` is rejected.
2. **Every surface is checked at the exit**, in this order: parse → catalog schema → per-agent
   component allow-list → no literal numbers in component props → tool data present this turn
   (→ bindings resolve to it). Anything that fails becomes a plain-text fallback. Raw model JSON
   never reaches the client. Where the check runs sets the retry budget. Layout written into
   the answer text (the prototype, `<a2ui-json>`): with the adk-architecture shell, run the check
   in the verify node and use its single retry (SH-2); after it the answer goes out without the
   surface (SH-3). Layout sent through a tool (`emit_ui` in adk-a2ui-integration): the same
   checks run inside the tool, which returns the errors to the model for at most two
   corrections. Prose next to the surface still goes through number verification.
3. **Actions are untrusted client input.** A button's context (`{"invoice_id": ...}`) goes
   through the same entitlement checks as a user message. An action turn updates the existing
   surface in place: upsert only the data-model keys the turn produced (`/selected`), so the
   rest (the list) stays.
4. **Formatting**: with adk-architecture, bind to the figure's code-formatted `display`; don't
   compute or format numbers in the client (`formatNumber`, `formatCurrency`, arithmetic). The
   prototype formatted in the browser; the ADR explains why that is not the default.
5. **No A2A needed.** Surfaces travel as events on your own API (SSE in the prototype). A2A
   is an optional second front door for the same payloads (adk-a2ui-integration).

## Backend (Python)

- Use `DirectJsonFormat("0.9", catalogs=[catalog])` and
  `format.prompt_generator.generate(role_description=..., workflow_description=...,
  ui_description=..., allowed_components=..., allowed_messages=["CreateSurfaceMessage",
  "UpdateComponentsMessage"], include_schema=True, include_examples=True,
  validate_examples=True)`. `A2uiSchemaManager` and `generate_system_prompt` are deprecated.
- Parse with `format.parser.parse_response(text)`. The model wraps JSON in
  `<a2ui-json>…</a2ui-json>`. On SDK 0.6.0 the parser also validates: it raises on unknown
  components, dangling child IDs and schema violations. **From 0.7.0 it only parses** (a missing
  close tag still raises); call `format.get_selected_catalog().validate(messages)` after it, or
  the catalog schema step of the exit check is silently skipped. That method does not exist in
  0.6.0; `a2ui_support.py` calls it when it is there, so it rejects the same layouts on both.
- Pass the prompt to `LlmAgent` as a callable (`instruction=lambda ctx: ...`) so ADK's `{state}`
  templating doesn't touch the embedded JSON schema. As a plain string the run fails with
  `KeyError: Context variable not found` on the first brace that looks like a key (2.11.0).
- Custom components: a catalog JSON file with its own `catalogId`, merged into the bundled basic
  catalog by a small provider (basic components `$ref` the catalog's own `$defs`, so the catalog
  must be self-contained). See `weather_catalog.py`.
- Few-shot examples (a validated layout JSON) are added to the prompt; the model copies them
  closely, so they shape the UI more than instructions do.
- Reference: `a2ui_support.py` (prompt, parse, allow-list, digit check), `api.py`
  (`_reply_events`, `_action_events`, per-key action updates, usage log).

## Frontend (React)

- One `MessageProcessor([customCatalog, basicCatalog], onAction)` per scope in which surface
  ids are unique. In a chat transcript where every answer brings its own surfaces that is **one
  per assistant turn** (the prototype), so a later turn's `createSurface` cannot touch an earlier
  answer's surface. A page with stable semantic ids (`limit_form`, `findings`) that are updated
  in place and tracked per session uses one processor for the page (`main.ts` in
  adk-a2ui-integration). Keep processors in a ref, not in state. Render `<A2uiSurface surface={...} />` from
  `@a2ui/react/v0_9`. See `a2ui.ts`, `A2uiView.tsx`.
- Custom components: derive each Zod schema from the same catalog JSON and hand-write only the
  render (`catalog.tsx`). The `Catalog` id must equal the `catalogId` in `createSurface`. Fail
  at startup when a catalog component has no implementation.
- No raw HTML: no `dangerouslySetInnerHTML`, and don't provide `MarkdownContext` (without it
  `Text` renders plain text).
- Actions arrive as `{name, surfaceId, sourceComponentId, timestamp, context}`; send them to the
  backend with the session ID and apply the returned messages to the processor that owns the
  surface.

## About the reference code

The files under [references/code/](references/code/) are **excerpts from the prototype, not a
runnable package**. They show the patterns above with real SDK calls; copy the shape, not the
files. `api.py` imports `app.events`, `app.paths`, `app.registry` and `app.config`, which are
not included (event models, path constants, the agent registry and `.env` loading are
project-specific). `a2ui_support.py`, `weather_catalog.py`, the two catalog JSON files and the
React files are self-contained.

## Pitfalls seen in the prototype

- `allowed_components` only prunes the prompt; the SDK validates against the full catalog.
  Enforce the allow-list yourself.
- `parse_and_fix` silently repairs model JSON (smart quotes, trailing commas, a single object
  wrapped into a list).
- Schema validation accepts numbers in text ("Temperature is 12.5 degrees"). The model also
  hides arithmetic in expressions (`${formatNumber(value: ${/t} * 1.8 + 32)}`). The digit check
  exempts only ids, child refs, `{"path"}`, plain `${path}` interpolations and catalog enum props
  (`variant: "h3"`); never exempt function expressions.
- Models reuse tool results from earlier turns and write a layout without calling tools; the
  surface then has no data. Tool descriptions must say results are current and must be fetched
  again each turn.
- The ready-made `a2ui.adk.send_a2ui_to_client_toolset` imports the A2A part converter. The SDK
  hard-depends on `a2a-sdk` even if you never import it.
- Cost: ~27k input tokens per answer with three model calls (the prompt carries ~25k characters
  of catalog schema), mostly served from Vertex implicit cache. Flash-Lite does no thinking by
  default. A small local model (qwen3:8b) skipped tools with the full prompt.
- React StrictMode runs state updaters twice: keep message processing out of `setState`
  updaters.
- In some Chromium builds `scrollIntoView` returns a Promise: use a block body in `useEffect`,
  never an arrow that returns the call.

## Checklists

**New A2UI agent**: allow-list of components → role, workflow and UI description (tool steps,
data-model shape, surface id) → validated few-shot example → data-model builder that reads only
this turn's tool results → offline tests: valid layout gets data, surface without tool data is
rejected, model data model rejected, unknown and non-allowed components rejected.

**New custom component**: add it to the catalog JSON → implement the React render → add it to
the agent's allow-list → update the examples → test it validates against the merged catalog.
