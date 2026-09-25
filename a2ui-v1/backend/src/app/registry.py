"""Agent registry: name -> root_agent, and whether its replies carry A2UI."""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from google.adk.agents import BaseAgent

from app.a2ui_support import A2uiSupport
from app.agents import chat, weather_ui


@dataclass(frozen=True)
class AgentEntry:
    name: str
    description: str
    root_agent: BaseAgent
    a2ui: Optional[A2uiSupport] = None  # None = plain text agent
    # Builds the surface data model from this turn's tool results ({tool name: response}).
    # None = no trustworthy data, so any surface is rejected.
    data_model: Callable[[dict[str, Any]], Optional[dict[str, Any]]] = lambda _: None

    @property
    def renders_a2ui(self) -> bool:
        return self.a2ui is not None


def weather_data_model(tool_results: dict[str, Any]) -> Optional[dict[str, Any]]:
    result = tool_results.get("get_weather")
    return result if result and "error" not in result else None


REGISTRY: dict[str, AgentEntry] = {
    e.name: e
    for e in [
        AgentEntry(
            "weather_ui",
            weather_ui.root_agent.description,
            weather_ui.root_agent,
            weather_ui.a2ui,
            weather_data_model,
        ),
        AgentEntry("chat", chat.root_agent.description, chat.root_agent),
    ]
}
