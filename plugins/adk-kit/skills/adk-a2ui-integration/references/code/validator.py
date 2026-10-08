"""A2UI v0.9.1 validation against vendored schemas plus local policy. No network, no a2ui SDK.

Vendor specification/v0_9_1/json/{server_to_client,client_to_server,common_types}.json and
specification/v0_9_1/catalogs/basic/catalog.json (or your merged catalog) from a pinned commit; there
is no v0.9.1 git tag, so use the SDK release tag (python/a2ui-agent-sdk/v0.7.0) or a commit SHA.
Model-written layout additionally goes through the digit check from a2ui-surfaces
(a2ui_support.py), which is not repeated here.
"""

import json
import pathlib
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from referencing import Registry
from referencing.jsonschema import DRAFT202012

A2UI_VERSION = "v0.9.1"
SCHEMA_DIR = pathlib.Path(__file__).resolve().parents[2] / "schemas" / "a2ui" / "v0_9_1"
SERVER_SCHEMA = "server_to_client.json"
CLIENT_SCHEMA = "client_to_server.json"
CATALOG_SCHEMA = "catalog.json"  # the basic catalog, or your merged catalog
# The v0.9.1 files still carry v0_9 $ids, and server_to_client.json refers to "catalog.json" relative
# to its $id: a slot for whichever catalog the app uses. Register the catalog there too.
CATALOG_SLOT = "https://a2ui.org/specification/v0_9/catalog.json"

# Per app; per agent if several agents emit UI. Image/Video left out on purpose (exfiltration beacons).
ALLOWED_COMPONENTS = {
    "Card", "Column", "Row", "List", "Tabs", "Text", "Icon", "Divider",
    "TextField", "CheckBox", "ChoicePicker", "DateTimeInput", "Button",
}
ALLOWED_EVENTS = {"submit_limit_request", "cancel", "show_details", "confirm"}
MAX_ACTION_BYTES = 4096


class A2uiValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def _load() -> tuple[Draft202012Validator, Draft202012Validator]:
    registry = Registry()
    docs: dict[str, Any] = {}
    for p in SCHEMA_DIR.glob("*.json"):
        doc = json.loads(p.read_text())
        docs[p.name] = doc
        registry = registry.with_resource(
            doc.get("$id", p.name), DRAFT202012.create_resource(doc))  # client_to_server.json has no $schema
    registry = registry.with_resource(CATALOG_SLOT, DRAFT202012.create_resource(docs[CATALOG_SCHEMA]))
    return (
        Draft202012Validator(docs[SERVER_SCHEMA], registry=registry),
        Draft202012Validator(docs[CLIENT_SCHEMA], registry=registry),
    )


_SERVER, _CLIENT = _load()


def validate_server_messages(msgs: list[dict], *, model_written: bool) -> list[dict]:
    """Raise A2uiValidationError with every problem found. model_written=True forbids data-model writes."""
    errors: list[str] = []
    for i, m in enumerate(msgs):
        m.setdefault("version", A2UI_VERSION)
        if m["version"] != A2UI_VERSION:
            errors.append(f"[{i}] version {m['version']} not supported")
        if err := best_match(_SERVER.iter_errors(m)):  # points at the failing component
            errors.append(f"[{i}] {err.json_path}: {err.message[:300]}")
        if m.get("createSurface", {}).get("sendDataModel"):
            errors.append(f"[{i}] sendDataModel is disabled")
        if model_written and "updateDataModel" in m:
            errors.append(f"[{i}] updateDataModel is written by the backend, not the model")
        comps = m.get("updateComponents", {}).get("components", [])
        ids = {c.get("id") for c in comps}
        for c in comps:
            if c.get("component") not in ALLOWED_COMPONENTS:
                errors.append(f"[{i}] component {c.get('component')!r} not allowed")
            action = c.get("action") or {}
            if "functionCall" in action:
                errors.append(f"[{i}] functionCall actions are disabled")
            event = action.get("event")
            if event and event.get("name") not in ALLOWED_EVENTS:
                errors.append(f"[{i}] event {event.get('name')!r} not allowed")
            refs = list(c.get("children") or []) if isinstance(c.get("children"), list) else []
            if "child" in c:
                refs.append(c["child"])
            errors += [f"[{i}] {c.get('id')} refers to missing {r}" for r in refs if r not in ids]
    if errors:
        raise A2uiValidationError(errors)
    return msgs


def validate_client_action(msg: dict) -> dict:
    if len(json.dumps(msg).encode()) > MAX_ACTION_BYTES:
        raise A2uiValidationError(["action too large"])
    errors = [e.message for e in _CLIENT.iter_errors(msg)]
    if errors:
        raise A2uiValidationError(errors)
    if "action" not in msg:  # the schema also allows {"error": ...}; handle those separately
        raise A2uiValidationError(["not an action"])
    if msg["action"]["name"] not in ALLOWED_EVENTS:
        raise A2uiValidationError(["unknown action"])
    return msg
