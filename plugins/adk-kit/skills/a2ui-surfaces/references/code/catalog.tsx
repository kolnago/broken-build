/**
 * The demo catalog: A2UI v0.9 basic catalog + custom components from catalog/weather_catalog.json.
 *
 * The JSON file is the single source of truth. The catalog id and each custom component's
 * Zod schema (prop names, types, required/optional) are derived from it here; only the
 * React rendering is hand-written. The backend merges the same file into its catalog
 * (backend/src/app/weather_catalog.py).
 */
import {basicCatalog, createComponentImplementation, type ReactComponentImplementation} from '@a2ui/react/v0_9';
import {Catalog, CommonSchemas} from '@a2ui/web_core/v0_9';
import {z} from 'zod';
import catalogJson from '../../catalog/weather_catalog.json';

type JsonProp = {$ref?: string; const?: string};
type JsonComponent = {allOf: {properties?: Record<string, JsonProp>; required?: string[]}[]};

/** `https://…/common_types.json#/$defs/DynamicString` → CommonSchemas.DynamicString */
function zodForProp(prop: JsonProp): z.ZodTypeAny {
  const name = prop.$ref?.split('#/$defs/')[1] as keyof typeof CommonSchemas | undefined;
  const schema = name && CommonSchemas[name];
  if (!schema) throw new Error(`Unsupported catalog prop: ${JSON.stringify(prop)}`);
  return schema as z.ZodTypeAny;
}

function apiFromJson(name: string) {
  const component = (catalogJson.components as Record<string, JsonComponent>)[name];
  const own = component.allOf.find(part => part.properties?.component?.const === name)!;
  const required = new Set(own.required ?? []);
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const [prop, spec] of Object.entries(own.properties ?? {})) {
    if (prop === 'component') continue;
    shape[prop] = required.has(prop) ? zodForProp(spec) : zodForProp(spec).optional();
  }
  return {name, schema: z.object(shape)};
}

/** Resolved props of WeatherCard (bindings already turned into values by the binder). */
type WeatherCardProps = {
  city?: string;
  temperature?: number;
  condition?: string;
  wind?: number;
  updatedAt?: string;
  refresh?: () => void;
};

const WeatherCard = createComponentImplementation(apiFromJson('WeatherCard'), ({props}) => {
  const p = props as WeatherCardProps;
  return (
    <div className="weather-card">
      <div className="weather-card__head">
        <h3>{p.city}</h3>
        <button onClick={p.refresh}>Refresh</button>
      </div>
      <div className="weather-card__temp">{p.temperature} °C</div>
      <div>{p.condition}</div>
      <div className="weather-card__meta">
        Wind {p.wind} km/h{p.updatedAt && <> · updated {p.updatedAt}</>}
      </div>
    </div>
  );
});

const customComponents: Record<string, ReactComponentImplementation> = {WeatherCard};

// Fail fast if the JSON declares a component that has no React implementation.
for (const name of Object.keys(catalogJson.components)) {
  if (!customComponents[name]) throw new Error(`No React implementation for ${name}`);
}

export const weatherCatalog = new Catalog<ReactComponentImplementation>(
  catalogJson.catalogId,
  [...basicCatalog.components.values(), ...Object.values(customComponents)],
  [...basicCatalog.functions.values()],
);
