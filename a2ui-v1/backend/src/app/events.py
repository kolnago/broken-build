"""Wire contract between backend and frontend.

Everything the frontend receives or sends is defined here. TypeScript types are generated
from these models (see `app.export_schema`), so the frontend never hand-writes them.
"""

from typing import Annotated, Any, Literal, Optional, Union

from a2ui.core.schema.client_to_server import A2uiClientAction
from pydantic import BaseModel, ConfigDict, Field


class Wire(BaseModel):
    # In serialization-mode JSON Schema, fields with defaults (e.g. `type`) are required.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class AgentInfo(Wire):
    name: str
    description: str
    renders_a2ui: bool


class ChatRequest(BaseModel):
    agent: str
    session_id: Optional[str] = None
    text: str = ""
    # A2UI v0.9 user action from a rendered surface (e.g. the WeatherCard Refresh button).
    action: Optional[A2uiClientAction] = None


# --- SSE events (one JSON object per `data:` line) -------------------------------------


class ProgressEvent(Wire):
    type: Literal["progress"] = "progress"
    tool: str


class A2uiEvent(Wire):
    type: Literal["a2ui"] = "a2ui"
    # Already parsed and validated A2UI v0.9 server-to-client messages.
    messages: list[dict[str, Any]]


class TextEvent(Wire):
    type: Literal["text"] = "text"
    text: str


class DoneEvent(Wire):
    type: Literal["done"] = "done"
    session_id: Optional[str] = None


class ErrorEvent(Wire):
    type: Literal["error"] = "error"
    message: str


StreamEvent = Annotated[
    Union[ProgressEvent, A2uiEvent, TextEvent, DoneEvent, ErrorEvent],
    Field(discriminator="type"),
]

