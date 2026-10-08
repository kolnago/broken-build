"""SSE route: own FastAPI endpoints streaming server-sent events. Same origin as the vendored client."""

import asyncio
import json

from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.adk.apps import App, ResumabilityConfig
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService  # or VertexAiSessionService
from google.genai import types

from app.actions import FormInvalid, handle_action
from app.agent import root_agent
from app.auth import current_user  # verifies the IAP / OIDC JWT; user id never comes from the client
from app.config import SETTINGS

app = FastAPI()
# App + Runner(app=...) makes plugins and resumability available. Resumability is needed for the
# Workflow variant with RequestInput (EXPERIMENTAL warning in 2.11); drop it otherwise.
runner = Runner(
    app=App(name="limit_advisor", root_agent=root_agent,
            resumability_config=ResumabilityConfig(is_resumable=True)),
    session_service=DatabaseSessionService(db_url=SETTINGS.session_db),
)


def to_sse(event) -> list[str]:
    out = []
    for response in event.get_function_responses() or []:
        payload = response.response or {}
        if payload.get("status") == "rendered" and payload.get("a2ui"):
            out.append({"type": "a2ui", "messages": payload["a2ui"]})
    if event.content and event.is_final_response():
        text = "".join(p.text or "" for p in event.content.parts if not getattr(p, "thought", False))
        if text:
            out.append({"type": "text", "text": text})  # already through number verification
    return [f"data: {json.dumps(o)}\n\n" for o in out]


async def _cancel_on_disconnect(request: Request, abort: asyncio.Event) -> None:
    # The built-in /run_sse cancels on client disconnect (2.11.0); own routes have to wire it.
    while not abort.is_set():
        if await request.is_disconnected():
            abort.set()
        await asyncio.sleep(1)


@app.post("/api/chat/{session_id}")
async def chat(session_id: str, body: dict, request: Request, user=Depends(current_user)):
    message = types.Content(role="user", parts=[types.Part(text=str(body["text"])[:8000])])

    async def stream():
        abort = asyncio.Event()
        watcher = asyncio.create_task(_cancel_on_disconnect(request, abort))
        try:
            async for ev in runner.run_async(user_id=user.id, session_id=session_id, new_message=message,
                                             abort_signal=abort):
                for chunk in to_sse(ev):
                    yield chunk
        finally:
            abort.set()
            watcher.cancel()

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/action/{session_id}")
async def action(session_id: str, body: dict, request: Request, user=Depends(current_user)):
    async def stream():
        abort = asyncio.Event()
        watcher = asyncio.create_task(_cancel_on_disconnect(request, abort))
        try:
            async for ev in handle_action(body, runner, user.id, session_id, abort_signal=abort):
                for chunk in to_sse(ev):
                    yield chunk
        except FormInvalid as e:  # the runner was not called; show the errors on the form
            yield f"data: {json.dumps({'type': 'form_errors', 'surfaceId': e.surface_id, 'errors': e.errors}, default=str)}\n\n"
        finally:
            abort.set()
            watcher.cancel()

    return StreamingResponse(stream(), media_type="text/event-stream")


app.mount("/", StaticFiles(directory="web/dist", html=True), name="web")
