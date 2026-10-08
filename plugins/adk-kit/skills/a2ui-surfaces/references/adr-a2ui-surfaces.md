# ADR-### Agent answers may include A2UI surfaces
Date: 2026-09-26
Status: proposed
Relates to: adk-architecture P1, P2, P7, §4, §8.5, §9 (VER-1, VER-3, SH-3), TOOL-3, LED-1,
SEC-2, SEC-4, OD-1, OD-9; specfirst IMPL-1

Drafted in the a2ui-v1 prototype. The evidence cited below ("NOTES step n", `backend/tests/`)
lives in that prototype repository and is **not part of this skill**; the observations are
summarised where they are cited, and the code excerpts under `code/` are what was kept. Verified against `a2ui-agent-sdk` 0.6.0, `google-adk` 2.9.2,
`@a2ui/react` 0.11.1, `@a2ui/web_core` 0.11.0; A2UI protocol v0.9. adk-next pins
`google-adk~=2.8`: anything ADK-specific below is `# VERIFY` there.

## Context

The analyst agent answers in prose. Some answers are better as a small interactive view: a list
with a detail, a card with actions ("draft reminder", "show breaches"). A2UI lets an agent
describe such a view as declarative JSON (layout, data bindings, inputs, actions) that the client
renders with its own trusted components. It is transport-agnostic; A2A is optional.

A surface is a new output channel. P1 and §9 guarantee that every number in *prose* traces to
the turn ledger; nothing yet covers numbers in a *UI*. A2UI also lets the client compute what is
displayed (`formatCurrency`, `formatNumber`, arithmetic inside expressions), which conflicts
with P7 and OD-1 (formatting is code, in `core/calc/`).

The prototype established how the pieces behave:
- Schema validation accepts model-written numbers in text ("Temperature is 12.5 degrees") and
  numbers hidden in client expressions (`${formatNumber(value: ${/t} * 1.8 + 32)}`). NOTES step 3.
- The SDK's `allowed_components` prunes the prompt only; validation accepts any catalog
  component. The SDK's parser silently repairs model JSON. NOTES step 0.
- The ready-made ADK integration imports A2A code. The SDK hard-depends on `a2a-sdk`. NOTES step 0.
- With the ledger reset per turn (LED-1), a model that remembers earlier tool results writes a
  layout without calling tools again; the surface then has no data. Observed with
  `gemini-3.1-flash-lite`, NOTES step 5 and the 2026-09-26 session.
- One answer with a surface costs ~27k input tokens (the generated prompt includes the catalog
  schema), mostly served from Vertex implicit cache. NOTES step 7.
- A small local model (`qwen3:8b`) skipped tools with the full prompt. Dropped. NOTES step 6.

## Decision

1. **The model writes layout; code writes data.** The model may emit only `createSurface` and
   `updateComponents`. Every `updateDataModel` is built by code from the **turn ledger**; a model
   `updateDataModel` is a violation. (Prototype: `a2ui_support.parse`, `registry.data_model`.)
2. **Components bind to figure views, not raw values.** The data model exposes TOOL-3 figure
   views; components show `display` (formatted in `core/calc/`, OD-1). Client functions that
   compute or format numbers (`formatNumber`, `formatCurrency`, arithmetic) are not allowed.
   Date formatting and `formatString` with plain path interpolation are allowed.
   *Differs from the prototype*, which bound raw values and formatted in the browser.
3. **Surfaces are verified at the exit, in the shell's verify node (§8.5).** Checks, in order:
   parse → catalog schema → per-agent component allow-list (our own; the SDK's is prompt-only) →
   no literal numbers in component props (ids, child refs, `{"path"}`, plain `${path}`
   interpolations and catalog enum props exempt) → every binding resolves to a ledger path →
   the turn has ledger data. Violations feed the VER-3 retry; after it, SH-3 applies and the
   answer is delivered **without** the surface. Raw model JSON never reaches the client.
   *Binding resolution and retry are new*; the prototype rejected at once.
4. **Prose next to a surface passes `verify_numbers` (§9)** like any answer.
5. **Actions are client input.** An action's context (e.g. `{"invoice_id": ...}`) is untrusted
   and goes through the same service entitlement checks as a user message (SEC-2, SEC-3).
   Fixed-meaning actions (select, refresh, page) are handled by code: action → tool →
   `updateDataModel` on the existing surface, no model call (P7). Actions that need judgement
   go to the agent. Action updates replace only the data-model keys the turn produced.
6. **Own transport, no A2A.** Surfaces travel as events on the existing API (SSE). Do not import
   `a2ui.a2a`, `a2ui.adk.a2a` or `a2ui.adk.send_a2ui_to_client_toolset`. Parse model text with
   `DirectJsonFormat` and generate prompts with `format.prompt_generator.generate`
   (`A2uiSchemaManager` / `generate_system_prompt` are deprecated in 0.6.0).
7. **One catalog file is the contract** between backend and frontend (custom components
   included). The frontend fails at startup if a component has no implementation. The client
   renders no raw HTML: no `dangerouslySetInnerHTML`, no markdown renderer for `Text`.
8. **Layer placement (§4).** The digit and binding checks are pure → `core/guardrails/`. Parsing,
   schema validation and prompt generation depend on `a2ui` → `workflows/` (verify node). The
   data-model builder reads the ledger → `tools/` or `workflows/`. Event types → `api/`.
9. **Dependencies (IMPL-1).** `a2ui-agent-sdk` (pulls `a2a-sdk` transitively, unused) on the
   backend; `@a2ui/react` and `@a2ui/web_core` on the frontend. Versions move together; the
   protocol version is pinned on both sides.

## Consequences

- Every surface number traces to the ledger, as prose does. A wrong *label* on a correct
  binding ("Max" over a min value) is not caught; custom components that own their labels
  (e.g. a card that prints the unit itself) reduce it. Consistency evals (TEST-3) cover the rest.
- Prompts grow by the catalog schema (~25k characters for a pruned basic catalog: 33k with it,
  8k without, NOTES step 6). Implicit
  caching absorbs most of the cost; a slimmer prompt is possible but was only tested on a local
  model.
- Tool docstrings (TOOL-2) must state that results are current and must be fetched again each
  turn; otherwise models reuse history and the surface fails the ledger check.
- Surfaces cannot stream through verification (OD-9): the whole answer is buffered.
- Models copy the few-shot layout closely. Examples shape the UI more than instructions do.
- Lists of records (master-detail) need a figure-view shape for rows; TOOL-3 defines flat
  figures only. See open questions.

## Alternatives considered

- **Fixed React screens, LLM only in prose or inside tools** — preferred whenever the layout does
  not depend on the data or on judgement. A2UI is justified only when the agent chooses the view.
- **Model writes the data model** — rejected: numbers cannot be traced (P1).
- **Client-side formatting of raw values** (the prototype's approach) — rejected for P7/OD-1;
  kept in the prototype as a learning artifact.
- **SDK's ADK/A2A integration** — rejected: pulls A2A into the runtime; our transport suffices.
- **Reusing earlier ledger data when a turn has none** — rejected: stale data looks current.
- **Local models via Ollama** — tried, dropped (NOTES step 6).

## Open questions

1. Figure-view shape for record lists (rows of figures) and how components bind to it.
2. Reusing validated layouts per view type, so refreshes need no model call.
3. Forms (`TextField`, `DateTimeInput`, …) and `sendDataModel`: how user-entered values are
   validated before they reach a tool.
4. Which basic-catalog functions are on the allow-list (decision 2 names the defaults).
