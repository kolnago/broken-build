"""HTTP API: GET /api/agents, POST /api/chat (Server-Sent Events)."""

import json
import logging
import re
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app import config  # noqa: F401  (loads .env before any model client is created)
from app.a2ui_support import A2uiRejected, update_data_model, with_data_model
from app.events import (
    A2uiClientAction,
    A2uiEvent,
    AgentInfo,
    ChatRequest,
    DoneEvent,
    ErrorEvent,
    ProgressEvent,
    TextEvent,
)
from app.registry import REGISTRY, AgentEntry

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app.api")

USER_ID = "demo-user"
UI_FALLBACK = "(The answer included a UI that failed validation, so it is not shown.)"
A2UI_BLOCK = re.compile(r"<a2ui-json>.*?(?:</a2ui-json>|$)", re.DOTALL)
A2UI_LOOKALIKE = re.compile(r'"(createSurface|updateComponents|updateDataModel)"')

app = FastAPI(title="a2ui-demo")
session_service = InMemorySessionService()
runners = {
    name: Runner(agent=e.root_agent, app_name=name, session_service=session_service)
    for name, e in REGISTRY.items()
}


@app.get("/api/agents")
def list_agents() -> list[AgentInfo]:
    return [
        AgentInfo(name=e.name, description=e.description, renders_a2ui=e.renders_a2ui)
        for e in REGISTRY.values()
    ]


@app.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    entry = REGISTRY.get(req.agent)
    if entry is None:
        raise HTTPException(404, f"Unknown agent: {req.agent}")
    return StreamingResponse(
        _sse(_run(entry, req)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _sse(events) -> AsyncIterator[str]:
    async for event in events:
        yield f"data: {event.model_dump_json()}\n\n"


async def _run(entry: AgentEntry, req: ChatRequest):
    session_id = None
    try:
        session_id = await _session_id(entry.name, req.session_id)
        final_text = ""
        text = _action_prompt(req.action) if req.action else req.text
        tool_results: dict = {}  # tool name -> latest response, captured from ADK events
        async for event in runners[entry.name].run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=text)]),
        ):
            for call in event.get_function_calls():
                yield ProgressEvent(tool=call.name)
            for resp in event.get_function_responses():
                tool_results[resp.name] = resp.response
            if event.is_final_response() and event.content and event.content.parts:
                final_text += "".join(
                    p.text for p in event.content.parts if p.text and not p.thought
                )

        replies = (
            _action_events(entry, req.action, tool_results)
            if req.action
            else _reply_events(entry, final_text, tool_results)
        )
        for out in replies:
            yield out
    except Exception:
        log.exception("chat failed (agent=%s)", entry.name)
        yield ErrorEvent(message="Something went wrong while answering. Please try again.")
    finally:
        yield DoneEvent(session_id=session_id)


def _action_prompt(action: A2uiClientAction) -> str:
    return f"UI action {action.name!r} with context {json.dumps(action.context)}"


def _action_events(entry: AgentEntry, action: A2uiClientAction, tool_results: dict):
    """Answer a UI action by updating the existing surface's data model in place.

    The model's reply text/A2UI is ignored: the layout already exists, and data only ever
    comes from tool results.
    """
    data = entry.data_model(tool_results)
    if data is None:
        yield TextEvent(text="Could not refresh the data.")
        return
    yield A2uiEvent(messages=[update_data_model(action.surface_id, data)])


def _reply_events(entry: AgentEntry, text: str, tool_results: dict):
    """Turn the model's final text into safe events. Raw model JSON is never forwarded."""
    if entry.a2ui is None:
        yield TextEvent(text=text)
        return

    if not entry.a2ui.has_a2ui(text):
        if A2UI_LOOKALIKE.search(text):  # JSON without tags: don't leak it as text
            log.warning("A2UI-like JSON without tags rejected")
            yield TextEvent(text=UI_FALLBACK)
        elif text.strip():
            yield TextEvent(text=text.strip())
        return

    try:
        reply = entry.a2ui.parse(text)
        data = entry.data_model(tool_results)
        if reply.messages and data is None:
            raise A2uiRejected("Surface without tool data")
    except A2uiRejected as e:
        log.warning("A2UI rejected: %s", e)
        prose = A2UI_BLOCK.sub("", text).strip()
        yield TextEvent(text=f"{prose}\n\n{UI_FALLBACK}".strip())
        return

    for t in reply.texts:
        yield TextEvent(text=t)
    if reply.messages:
        yield A2uiEvent(messages=with_data_model(reply, data))


async def _session_id(app_name: str, requested: str | None) -> str:
    if requested:
        existing = await session_service.get_session(
            app_name=app_name, user_id=USER_ID, session_id=requested
        )
        if existing:
            return existing.id
    session = await session_service.create_session(app_name=app_name, user_id=USER_ID)
    return session.id
