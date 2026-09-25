from google.adk.agents import LlmAgent

from app.a2ui_support import A2uiSupport
from app.config import MODEL
from app.paths import CATALOG_DIR
from app.weather import get_weather
from app.weather_catalog import weather_catalog_config

a2ui = A2uiSupport(
    allowed_components=["WeatherCard", "Column", "Row", "Text"],
    catalog=weather_catalog_config(),
    examples_path=str(CATALOG_DIR / "examples" / "weather_layout.json"),
)

ROLE = "You are a weather assistant. You show the weather as a small UI card."

WORKFLOW = """
- Always call the `get_weather` tool for the requested city before answering.
- If the tool returns an error, answer in plain text only (no A2UI block).
- Otherwise answer with one short sentence WITHOUT any numbers, followed by exactly one
  A2UI JSON block.
- The A2UI block contains LAYOUT ONLY: createSurface and updateComponents. Never send
  updateDataModel; the application fills the data model with the exact `get_weather` result.
- When the message is a UI action "refresh" with a city in its context, call `get_weather`
  for that city again and reply with just "Refreshed." (no A2UI block).
- Never write a number into a component. Every value from the tool must be a data binding:
  {"path": "/temperature_c"}, or a formatString like "${/temperature_c} °C".
"""

UI = f"""
Build a single surface with surfaceId "weather" and catalogId "{a2ui.catalog_id}".
The data model is exactly the `get_weather` result:
  /city, /country, /temperature_c, /condition, /wind_kmh, /fetched_at,
  /forecast (a list of items with: date, min_c, max_c, condition).
Use one WeatherCard for the current weather (bind city, temperature, condition, wind,
updatedAt; its refresh action is the event "refresh" with context {{"city": {{"path": "/city"}}}}),
followed by the forecast list.
For the forecast, use a template child list {{"componentId": ..., "path": "/forecast"}} and
paths relative to the list item (e.g. "min_c").
"""

root_agent = LlmAgent(
    name="weather_ui",
    model=MODEL,
    description="Weather assistant that answers with an A2UI card.",
    # An InstructionProvider (callable) bypasses ADK's {state} templating, which would
    # otherwise scan the JSON schema embedded in the prompt for {placeholders}.
    instruction=lambda _ctx: a2ui.system_prompt(ROLE, WORKFLOW, UI),
    tools=[get_weather],
)
