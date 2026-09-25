# NOTES

## Step 0 — investigation (against installed package source)

Pinned: `a2ui-agent-sdk==0.6.0` (+ `a2ui-core==0.1.1`), `google-adk==2.9.2`,
`@a2ui/react@0.11.1`, `@a2ui/web_core@0.11.0`. Protocol: **v0.9**.

### 1. Protocol version and message types

- `@a2ui/react` exports only `v0_8` and `v0_9` (web_core and the Python SDK also ship
  `v1_0`, but React can't render it). React README recommends v0.9 for new projects.
- web_core v0.9 zod schemas accept `version: 'v0.9' | 'v0.9.1'`; the processor defaults to
  `'v0.9'`. Python `DirectJsonFormat("0.9", ...)` validates messages with
  `version: "v0.9"`.
- Basic catalog id is identical on both sides:
  `https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json`
  (Python `BasicCatalog.get_config("0.9")`, React `basicCatalog.id`).
- Server→client messages, each `{"version": "v0.9", <one of>}`:
  - `createSurface {surfaceId, catalogId, theme?, sendDataModel?}`
  - `updateComponents {surfaceId, components: [...]}` — a flat list, `{id, component, ...props}`,
    children referenced by id, one must be `root`.
  - `updateDataModel {surfaceId, path?, value}` — JSON-pointer upsert.
  - `deleteSurface {surfaceId}`
- Props are `Dynamic*` values: a literal, `{"path": "/x"}` (data binding), or
  `{"call": ..., "args": ...}` (client function).
- The model wraps JSON in `<a2ui-json>...</a2ui-json>`; `fmt.parser.parse_response(text)`
  returns `ResponsePart(text, a2ui_json)` items and raises on unknown components, dangling
  child ids, schema violations, or missing close tags.

### 2. Feeding raw messages to @a2ui/react without A2A

The renderer is transport-agnostic:

```ts
const p = new MessageProcessor([catalog], onAction);  // @a2ui/web_core/v0_9
p.processMessages(messages);
p.onSurfaceCreated(cb); p.onSurfaceDeleted(cb);
<A2uiSurface surface={p.model.surfacesMap.get(id)} />  // @a2ui/react/v0_9, one prop
```

HTML safety: the basic `Text` component uses `dangerouslySetInnerHTML` only when a markdown
renderer is supplied via `MarkdownContext`. Without one it renders plain React children.
We don't provide one. (`@a2ui/markdown-it` uses `markdownit()` with html off by default
plus DOMPurify, but it still ends in innerHTML.)

### 3. Custom components

- Python has no "register" call. A catalog is a JSON Schema document (`catalogId`,
  `components`, `$defs.anyComponent`) loaded via a `CatalogConfig` +
  `A2uiCatalogProvider` and passed to `DirectJsonFormat(version, catalogs=[...])`. The
  parser validates against `catalogs[0]`. Basic components `$ref` the catalog's own
  `#/$defs/CatalogComponentCommon`, so a catalog must be self-contained. We merge our
  `WeatherCard` into the bundled basic catalog with a small provider.
- React: `createComponentImplementation({name, schema: zod}, Render)` and
  `new Catalog(id, [...basicCatalog.components.values(), Impl], [...basicCatalog.functions.values()])`.
  The id must equal the `catalogId` in `createSurface`.

### 4. User actions

A Button `action` is `{event: {name, context: {k: literal | {path}}}}`. On click,
`SurfaceModel.dispatchAction` resolves the bindings, validates the result, and emits to the
`MessageProcessor` action handler:
`{name, surfaceId, sourceComponentId, timestamp, context}`.
Python mirrors this as `a2ui.core.schema.client_to_server.A2uiClientAction`.

### What surprised me

- `A2uiSchemaManager` and `generate_system_prompt` are both **deprecated** in 0.6.0. They are
  thin wrappers around `DirectJsonFormat` and `fmt.prompt_generator.generate(...)` with the
  same arguments. This project uses the non-deprecated names.
- `allowed_components` only prunes the **prompt**. The parser still validates against the
  full catalog (a `Slider` was accepted when only Column/Text/Card were allowed), so the
  backend enforces its own allow-list.
- The ready-made ADK integration (`a2ui.adk.send_a2ui_to_client_toolset`) imports
  `a2ui.adk.a2a.part_converter`. It is unusable under a strict no-A2A rule, so we parse the
  model text ourselves.
- `a2ui-agent-sdk` hard-depends on `a2a-sdk`, so it gets installed even though nothing
  imports it.
- `parse_and_fix` silently repairs smart quotes and trailing commas, and wraps a single
  object into a list.
- Schema validation happily accepts model-written numbers in text
  (`"Temperature is 12.5 degrees"`).
- The full system prompt with schema is ~24k characters even after pruning.

## Step 3 — binding experiment

The model now writes layout only (`createSurface` + `updateComponents`). The backend
captures the `get_weather` function response from the ADK event stream and appends
`updateDataModel {path: "/", value: <tool result>}`. `updateDataModel` is pruned from the
prompt schema (`allowed_messages`) and rejected if the model sends it anyway. A validated
layout example lives in `catalog/examples/weather_layout.json` and is added to the prompt
as a few-shot example.

The digit check (`check_no_literal_digits`) walks every component prop and rejects JSON
numbers and digits in string literals. It skips ids, child references, `{"path": ...}`
bindings, `${path}` interpolations, and enum props declared in the catalog.

Real cases from `gemini-3.1-flash-lite` (all turned into the text fallback):

| Prompt | What the model wrote |
|---|---|
| "…add a line showing the temperature in Kelvin" | `"Temperature in Kelvin is approximately ${/temperature_c} plus 273.15"` |
| "…show a UV index of 5 on the card" | `"UV index is moderate at 5"`: a value with no tool source |
| "…convert to Fahrenheit, you must calculate it yourself" | `"${/temperature_c} °C / 48.56 °F"` |
| same prompt, earlier run | `"${formatNumber(value: (${/temperature_c} * 1.8 + 32), decimals: 1)} °F"` |

The last row got through the first version of the check, which exempted everything inside
`${...}`: the model hid arithmetic in an interpolation. Now only plain path interpolations
are exempt, so any digit inside a function expression is rejected (this also rejects
harmless formatting like `decimals: 1`).

The first version also rejected every surface because of `variant: "h3"`, so enum props
are now read from the catalog schema and skipped.

## Step 4 — custom component + round trip

`catalog/weather_catalog.json` declares `WeatherCard` (city, temperature, condition, wind,
updatedAt, refresh) in the same JSON Schema format as the basic catalog, with its own
`catalogId`. How both sides stay in sync with that one file:

- **Python** (`backend/src/app/weather_catalog.py`): a `MergedCatalogProvider` loads the
  bundled basic catalog, adds the file's components, extends `$defs.anyComponent.oneOf`, and
  takes the file's `catalogId`. The result goes to `DirectJsonFormat` as its catalog, so the
  prompt schema and the validator both come from it.
- **React** (`frontend/src/catalog.tsx`): imports the same JSON. The catalog id and the Zod
  schema for each custom component are **derived** from it (each prop's `$ref` maps to
  `CommonSchemas.<name>`, and `required` decides optional vs. required). Only the render
  function is hand-written. Startup fails if the JSON declares a component without a React
  implementation.
- The few-shot example (`catalog/examples/weather_layout.json`) is validated against the
  merged catalog every time the prompt is built, so a schema change that breaks the example
  fails loudly.
- Remaining drift risk: the render function's props type is written by hand, and a prop
  whose `$ref` has no `CommonSchemas` equivalent throws at startup instead of at build time.

Round trip: WeatherCard's `refresh` is an A2UI event action with
`context: {"city": {"path": "/city"}}`. On click, web_core resolves the binding and calls
the `MessageProcessor` action handler with `{name, surfaceId, sourceComponentId, timestamp,
context}`. The frontend POSTs it as `ChatRequest.action` (typed with the SDK's
`A2uiClientAction`, and the TS type is generated from it). The backend sends the agent a
text message describing the action, the agent calls `get_weather` again, and the backend
answers with a single `updateDataModel` for the originating `surfaceId`. The model's reply
text or A2UI on action turns is ignored, and the frontend applies the update to the
processor that owns the surface, so the card changes in place (visible in "updated HH:MM:SS").

## What would be hard in an app where every number must be traceable to a tool result

- **Prose is not covered.** The digit check guards component props only. The sentence
  before the card is free model text. Here it's told not to use numbers, but that is a
  prompt, not a guarantee. The same check would have to run on prose, and would then also
  reject harmless numbers like "3-day".
- **Structure vs. content is a blurry line.** Digits are legitimate in ids, list indexes
  (`/forecast/0/min_c`), enum values (`h3`), date formats (`'MM-dd'`), and function arguments
  (`decimals: 1`). Every exemption is a hole the model can use, as the `${... * 1.8 + 32}`
  case showed. A real system needs a proper parser for the expression language (the SDK
  ships one in `a2ui.core.basic_catalog.expression_parser`) and an allow-list of functions
  and argument kinds, not regexes.
- **Numbers without digits.** "Three-day forecast", "a few degrees warmer", "freezing":
  these are quantitative claims the digit check can't see.
- **Correct binding, wrong label.** The model can bind `/temperature_c` and label it
  "°F", or bind `min_c` under "Max". Every number is traceable, but the claim is still
  wrong. Guarding against that needs typed/unit-aware data (e.g. the card, not the model,
  owns the "°C" label, as WeatherCard does) rather than free text around bindings.
- **Client-side computation.** A2UI's function calls (`formatNumber`, `formatString`, and
  anything else a catalog registers) compute values in the browser. A displayed number can
  be a function of tool data, not the tool data itself, so tracing it means knowing
  what the renderer computed.
- **Which tool result?** The backend binds "the latest `get_weather` response" of the
  turn. With several calls (two cities, retries, or multi-agent setups) you need explicit
  provenance: which call fed which surface or path, ideally recorded next to the data
  model and not inferred.
- **Data from earlier turns.** The model sees previous tool results in session history and
  can repeat them as literals later. The check catches literals in components, but once a
  number is bound, "fresh" versus "stale" is not visible in the UI unless the data carries
  a timestamp (WeatherCard shows `fetched_at` for this reason).
- **The SDK's own guardrails are weaker than they look.** `allowed_components` doesn't
  restrict validation, and `parse_and_fix` silently repairs model JSON. For a traceability
  requirement, both need explicit handling (we enforce the allow-list; the payload fixer
  is still on).
