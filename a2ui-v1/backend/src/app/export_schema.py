"""Print the JSON Schema of the wire types (input for json-schema-to-typescript).

    uv run python -m app.export_schema > ../frontend/src/api/wire.schema.json

Events are exported in "serialization" mode, so fields with defaults (like `type`) are
required and TypeScript can narrow on `event.type`. Requests use "validation" mode, so
optional fields stay optional.
"""

import json

from pydantic import TypeAdapter
from pydantic.json_schema import models_json_schema

from app.events import AgentInfo, ChatRequest, StreamEvent


def _strip_property_titles(node):
    if isinstance(node, dict):
        for prop in node.get("properties", {}).values():
            prop.pop("title", None)
        for value in node.values():
            _strip_property_titles(value)
    elif isinstance(node, list):
        for item in node:
            _strip_property_titles(item)


def build_schema() -> dict:
    _, defs = models_json_schema(
        [(AgentInfo, "serialization"), (ChatRequest, "validation")]
    )
    events = TypeAdapter(StreamEvent).json_schema(
        mode="serialization", ref_template="#/$defs/{model}"
    )
    all_defs = {**defs["$defs"], **events.pop("$defs")}
    all_defs["StreamEvent"] = {"title": "StreamEvent", **events}
    schema = {
        "title": "WireTypes",
        "type": "object",
        "properties": {name: {"$ref": f"#/$defs/{name}"} for name in all_defs},
        "$defs": all_defs,
    }
    _strip_property_titles(schema)
    return schema


if __name__ == "__main__":
    print(json.dumps(build_schema(), indent=2))
