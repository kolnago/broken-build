"""Server-built A2UI forms: deterministic, reviewable, golden-tested. Property names (label, variant,
checks) must match the vendored catalog - the validator rejects them otherwise."""

from .validator import A2UI_VERSION


def limit_request_form(surface_id: str, catalog_id: str, account_masked: str) -> list[dict]:
    v = A2UI_VERSION
    return [
        {"version": v, "createSurface": {"surfaceId": surface_id, "catalogId": catalog_id,
                                         "sendDataModel": False}},
        {"version": v, "updateComponents": {"surfaceId": surface_id, "components": [
            {"id": "root", "component": "Card", "child": "col"},
            {"id": "col", "component": "Column", "children": ["title", "acct", "amt", "reason", "row"]},
            {"id": "title", "component": "Text", "text": "Overdraft limit request", "variant": "h3"},
            {"id": "acct", "component": "Text", "text": {"path": "/form/accountMasked"}},
            {"id": "amt", "component": "TextField", "label": "Requested limit (EUR)",
             "value": {"path": "/form/amount"}},
            {"id": "reason", "component": "TextField", "label": "Reason", "value": {"path": "/form/reason"}},
            {"id": "row", "component": "Row", "children": ["cancel", "submit"]},
            {"id": "cancel", "component": "Button", "child": "cancel_lbl",
             "action": {"event": {"name": "cancel"}}},
            {"id": "cancel_lbl", "component": "Text", "text": "Cancel"},
            {"id": "submit", "component": "Button", "child": "submit_lbl",
             "checks": [{"condition": {"call": "required", "args": {"value": {"path": "/form/amount"}}},
                         "message": "Required"}],
             "action": {"event": {"name": "submit_limit_request", "context": {
                 "amount": {"path": "/form/amount"}, "reason": {"path": "/form/reason"}}}}},
            {"id": "submit_lbl", "component": "Text", "text": "Submit"},
        ]}},
        {"version": v, "updateDataModel": {"surfaceId": surface_id, "path": "/form",
                                           "value": {"accountMasked": account_masked, "amount": "", "reason": ""}}},
    ]
