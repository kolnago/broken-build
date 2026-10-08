"""User actions from A2UI surfaces: untrusted input. Transactions run in code, not in the model."""

import asyncio
import json

from google.genai import types
from pydantic import ValidationError

from app.a2ui.validator import validate_client_action
from app.limits import LimitRequest, coerce_limit_request, submit_limit_request  # pydantic-validated, entitlement-checked

DETERMINISTIC = {"submit_limit_request", "cancel"}
# Workflow variant: surface id -> the Pydantic model its form node passes as RequestInput.response_schema.
FORMS = {"limit_form": LimitRequest}


class FormInvalid(Exception):
    """The action context does not match the form's model. Sent back to the UI; the runner is not called."""

    def __init__(self, surface_id: str, errors: list[dict]):
        super().__init__(f"{surface_id}: {len(errors)} error(s)")
        self.surface_id, self.errors = surface_id, errors


async def handle_action(raw: dict, runner, user_id: str, session_id: str,
                        abort_signal: asyncio.Event | None = None):
    action = validate_client_action(raw)["action"]
    session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id)
    if session is None or action["surfaceId"] not in session.state.get("ui:surfaces", []):
        raise PermissionError("surface not owned by this session")

    interrupt_id = session.state.get("ui:interrupts", {}).get(action["surfaceId"])
    if interrupt_id:
        message = _resume_message(action, interrupt_id)
    elif action["name"] in DETERMINISTIC:
        result = await submit_limit_request(user_id, coerce_limit_request(action["context"]))
        note = f"[UI_ACTION_RESULT] {action['name']} -> {json.dumps(result)}"
        message = types.Content(role="user", parts=[types.Part(text=note)])
    else:
        note = "[UI_ACTION] " + json.dumps(
            {"name": action["name"], "surfaceId": action["surfaceId"], "context": action["context"]})[:4000]
        message = types.Content(role="user", parts=[types.Part(text=note)])

    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message,
                                        abort_signal=abort_signal):
        yield event


def _resume_message(action: dict, interrupt_id: str) -> types.Content:
    """Workflow variant (ADK 2.0). The form node yields RequestInput(message=..., response_schema=Model)
    and records its interrupt_id under state["ui:interrupts"][surface_id]. Verified on google-adk
    2.11.0: the pending function call is named "adk_request_input" and its id equals the interrupt_id;
    ADK validates and coerces the answer against response_schema ("500" -> 500); an invalid answer
    raises WorkflowDataError out of run_async, and that interrupt then keeps failing in the session,
    even for a later valid answer. So validate against the same model first and never resume with
    an invalid answer."""
    try:
        validated = FORMS[action["surfaceId"]].model_validate(action["context"])
    except ValidationError as e:
        raise FormInvalid(action["surfaceId"], e.errors(include_input=False, include_url=False)) from e
    response = types.FunctionResponse(id=interrupt_id, name="adk_request_input", response=validated.model_dump())
    return types.Content(role="user", parts=[types.Part(function_response=response)])
