"""A2UI prompt generation and response parsing (Direct JSON inference format, protocol v0.9).

The spec for this prototype names `A2uiSchemaManager.generate_system_prompt`. In
a2ui-agent-sdk 0.6.0 both are deprecated wrappers around `DirectJsonFormat` and
`prompt_generator.generate(...)` with the same arguments, so we use those directly.

Binding policy: the model writes LAYOUT only (createSurface + updateComponents, values bound
to data-model paths). The backend writes the data model from tool results. `parse` enforces
this: no updateDataModel from the model, and no literal digits in component props.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from a2ui.basic_catalog import BasicCatalog
from a2ui.inference_formats.direct_json.format import DirectJsonFormat
from a2ui.schema.catalog import CatalogConfig

log = logging.getLogger(__name__)

A2UI_VERSION = "0.9"  # must match @a2ui/web_core/v0_9 (accepts "v0.9")
LAYOUT_MESSAGES = ["CreateSurfaceMessage", "UpdateComponentsMessage"]

# Props whose string values are component ids or data paths, not displayed content.
NON_CONTENT_KEYS = {"id", "component", "child", "children", "componentId", "path"}
DIGIT = re.compile(r"\d")
# `${/a/b/0}` or `${a/b}`: first segment starts with a letter, later segments may be indexes.
PATH_INTERPOLATION = re.compile(r"(?<!\\)\$\{\s*/?[A-Za-z_][\w-]*(?:/[\w-]+)*\s*\}")


class A2uiRejected(Exception):
    """The model's A2UI failed parsing, validation, or our own checks."""


@dataclass
class ParsedReply:
    texts: list[str] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)

    @property
    def surface_ids(self) -> list[str]:
        return [m["createSurface"]["surfaceId"] for m in self.messages if "createSurface" in m]


class A2uiSupport:
    def __init__(
        self,
        allowed_components: list[str],
        catalog: Optional[CatalogConfig] = None,
        examples_path: Optional[str] = None,
    ):
        self.allowed_components = allowed_components
        catalog = catalog or BasicCatalog.get_config(A2UI_VERSION)
        if examples_path:
            catalog.examples_path = examples_path
        self.format = DirectJsonFormat(A2UI_VERSION, catalogs=[catalog])
        self.catalog_id = self.format.supported_catalog_ids[0]
        self.enum_props = _enum_props(self.format.get_selected_catalog().catalog_schema)

    def system_prompt(self, role: str, workflow: str = "", ui: str = "") -> str:
        return self.format.prompt_generator.generate(
            role_description=role,
            workflow_description=workflow,
            ui_description=ui,
            allowed_components=self.allowed_components,
            allowed_messages=LAYOUT_MESSAGES,
            include_schema=True,
            include_examples=True,
            validate_examples=True,
        )

    def has_a2ui(self, text: str) -> bool:
        return self.format.parser.has_format_content(text)

    def parse(self, text: str) -> ParsedReply:
        """Parse + validate a model reply. Raises A2uiRejected on any problem."""
        try:
            parts = self.format.parser.parse_response(text)
        except Exception as e:  # A2uiParseError / A2uiCompilationError / ...
            raise A2uiRejected(str(e)) from e

        reply = ParsedReply()
        for part in parts:
            if part.text and part.text.strip():
                reply.texts.append(part.text.strip())
            if part.a2ui_json is not None:
                reply.messages.extend(part.a2ui_json)

        for msg in reply.messages:
            if "updateDataModel" in msg:
                raise A2uiRejected("The model must not write the data model")
            for comp in msg.get("updateComponents", {}).get("components", []):
                self._check_allowed(comp)
                check_no_literal_digits(comp, self.enum_props.get(comp.get("component"), set()))
        return reply

    def _check_allowed(self, comp: dict[str, Any]) -> None:
        # The SDK validates against the whole catalog; `allowed_components` only
        # prunes the prompt. Enforce the allow-list ourselves.
        if comp.get("component") not in self.allowed_components:
            raise A2uiRejected(f"Component '{comp.get('component')}' is not allowed")


def with_data_model(reply: ParsedReply, data: dict[str, Any]) -> list[dict[str, Any]]:
    """The model's layout messages followed by backend-written data for each surface."""
    return reply.messages + [update_data_model(sid, data) for sid in reply.surface_ids]


def update_data_model(surface_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"version": "v0.9", "updateDataModel": {"surfaceId": surface_id, "path": "/", "value": data}}


def _enum_props(catalog_schema: dict[str, Any]) -> dict[str, set[str]]:
    """Component name -> props constrained to a fixed enum (e.g. Text.variant = "h3")."""
    result: dict[str, set[str]] = {}
    for name, comp in catalog_schema.get("components", {}).items():
        for part in comp.get("allOf", []):
            for prop, spec in part.get("properties", {}).items():
                if isinstance(spec, dict) and "enum" in spec:
                    result.setdefault(name, set()).add(prop)
    return result


def check_no_literal_digits(comp: dict[str, Any], enum_props: set[str] = frozenset()) -> None:
    """Reject a component if any displayed prop carries a model-written number.

    Allowed: bindings ({"path": ...}), `${path}` interpolations inside formatString, ids,
    and enum props from the catalog (their values come from a fixed list, like "h3").
    Rejected: JSON numbers, and digits anywhere else in a string literal.
    """

    def walk(value: Any, key: str, where: str, depth: int) -> None:
        if key in NON_CONTENT_KEYS or (depth == 1 and key in enum_props):
            return
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, (int, float)):
            raise A2uiRejected(f"Literal number {value!r} in {where}")
        if isinstance(value, str):
            literal = _strip_path_interpolations(value)
            if DIGIT.search(literal):
                raise A2uiRejected(f"Literal digit in {where}: {value!r}")
        elif isinstance(value, dict):
            for k, v in value.items():
                walk(v, k, f"{where}.{k}", depth + 1)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, key, f"{where}[{i}]", depth + 1)

    walk(comp, "", f"component '{comp.get('id')}'", 0)


def _strip_path_interpolations(s: str) -> str:
    """Remove plain data-path interpolations like `${/forecast/0/min_c}` or `${min_c}`.

    Only paths are exempt (their digits are list indexes, not values). Function calls
    such as `${formatNumber(value: ${/t} * 1.8 + 32)}` keep their text, so digits written
    inside an expression are still caught.
    """
    while True:
        stripped = PATH_INTERPOLATION.sub("", s)
        if stripped == s:
            return s
        s = stripped
