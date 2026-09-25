"""Reply handling without a model: valid layouts get tool data, anything else becomes text."""

import json

import pytest

from app.a2ui_support import A2uiRejected, check_no_literal_digits
from app.api import UI_FALLBACK, _reply_events
from app.registry import REGISTRY

WEATHER = REGISTRY["weather_ui"]
CID = WEATHER.a2ui.catalog_id
TOOL = {"get_weather": {"city": "Prague", "temperature_c": 9.2}}


def msgs(components):
    return [
        {"version": "v0.9", "createSurface": {"surfaceId": "w", "catalogId": CID}},
        {"version": "v0.9", "updateComponents": {"surfaceId": "w", "components": components}},
    ]


def events(text, tools=TOOL):
    return [e.model_dump() for e in _reply_events(WEATHER, text, tools)]


def wrap(payload):
    return f"Here it is.\n<a2ui-json>{json.dumps(payload)}</a2ui-json>"


BOUND = {"id": "root", "component": "Text", "text": {"path": "/temperature_c"}}


def is_fallback(out):
    return len(out) == 1 and out[0]["type"] == "text" and UI_FALLBACK in out[0]["text"]


def test_layout_gets_backend_data_model():
    out = events(wrap(msgs([BOUND])))
    assert [e["type"] for e in out] == ["text", "a2ui"]
    assert out[1]["messages"][-1]["updateDataModel"] == {
        "surfaceId": "w", "path": "/", "value": TOOL["get_weather"]}


def test_surface_without_tool_data_is_rejected():
    assert is_fallback(events(wrap(msgs([BOUND])), tools={}))


def test_model_written_data_model_is_rejected():
    payload = msgs([BOUND]) + [{"version": "v0.9", "updateDataModel": {
        "surfaceId": "w", "path": "/", "value": {"temperature_c": 30}}}]
    assert is_fallback(events(wrap(payload)))


def test_unknown_component_is_rejected():
    assert is_fallback(events(wrap(msgs([{"id": "root", "component": "Blink", "text": "x"}]))))


def test_catalog_component_outside_allow_list_is_rejected():
    slider = {"id": "root", "component": "Slider", "value": {"path": "/v"}, "min": 0, "max": 5}
    assert is_fallback(events(wrap(msgs([slider]))))


def test_json_without_tags_is_not_forwarded():
    raw = json.dumps(msgs([BOUND]))
    assert events(raw) == [{"type": "text", "text": UI_FALLBACK}]


@pytest.mark.parametrize("text", [
    {"path": "/forecast/0/min_c"},
    {"call": "formatString", "args": {"value": "${/temperature_c} °C"}},
    {"call": "formatString", "args": {"value": "${formatDate(value:${date}, format:'MM-dd')}"}},
    "Wind",
])
def test_digit_check_allows_bindings(text):
    check_no_literal_digits({"id": "row2", "component": "Text", "text": text})


@pytest.mark.parametrize("text", [
    "9.2 °C",
    {"call": "formatString", "args": {"value": "${/temperature_c} °C (48 °F)"}},
    {"call": "formatString", "args": {"value": "Next 3 days"}},
    # Real model output: arithmetic hidden inside an interpolation.
    {"call": "formatString", "args": {"value":
        "${formatNumber(value: (${/temperature_c} * 1.8 + 32), decimals: 1)} °F"}},
    # Real model output: a fabricated value.
    "UV index is moderate at 5",
    {"call": "formatString", "args": {"value": "${32}"}},
])
def test_digit_check_rejects_literals(text):
    with pytest.raises(A2uiRejected):
        check_no_literal_digits({"id": "t", "component": "Text", "text": text})


def test_digit_check_rejects_json_numbers_in_action_context():
    button = {"id": "b", "component": "Button", "child": "l",
              "action": {"event": {"name": "refresh", "context": {"days": 3}}}}
    with pytest.raises(A2uiRejected):
        check_no_literal_digits(button)


def test_enum_props_are_not_content():
    assert "variant" in WEATHER.a2ui.enum_props["Text"]
    out = events(wrap(msgs([{**BOUND, "variant": "h3"}])))
    assert [e["type"] for e in out] == ["text", "a2ui"]


def test_action_updates_existing_surface_with_tool_data_only():
    from app.api import _action_events
    from app.events import ChatRequest

    req = ChatRequest.model_validate({"agent": "weather_ui", "action": {
        "name": "refresh", "surfaceId": "weather", "sourceComponentId": "card",
        "timestamp": "2026-09-25T07:44:46Z", "context": {"city": "Prague"}}})
    out = [e.model_dump() for e in _action_events(WEATHER, req.action, TOOL)]
    assert out == [{"type": "a2ui", "messages": [{"version": "v0.9", "updateDataModel": {
        "surfaceId": "weather", "path": "/", "value": TOOL["get_weather"]}}]}]
    assert [e.type for e in _action_events(WEATHER, req.action, {})] == ["text"]


def test_custom_component_validates_against_merged_catalog():
    card = {"id": "root", "component": "WeatherCard", "city": {"path": "/city"},
            "temperature": {"path": "/temperature_c"}, "condition": {"path": "/condition"},
            "wind": {"path": "/wind_kmh"},
            "refresh": {"event": {"name": "refresh", "context": {"city": {"path": "/city"}}}}}
    assert [e["type"] for e in events(wrap(msgs([card])))] == ["text", "a2ui"]
    assert is_fallback(events(wrap(msgs([{**card, "temperature": 12}]))))
    assert is_fallback(events(wrap(msgs([{k: v for k, v in card.items() if k != "refresh"}]))))
