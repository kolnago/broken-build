# App

An output built from bricks, such as a container image. Not a brick: it holds no logic of its
own. If code in an app decides or computes anything, that code belongs in a brick.

## Shape

```
apps/
├── README.md              lists every app and what it builds
└── web-sample-1/
    ├── server.py          ADK's HTTP API over the bricks it names, plus the built frontend
    ├── test_server.py     what is served, and that nothing else is
    ├── frontend/          React with the A2UI renderer
    └── Dockerfile         stage 1 builds the frontend, stage 2 installs the bricks
```

ADK's stock app (`get_fast_api_app`) is a developer server: it runs any agent in the folder
and serves sessions, artifacts, `/run`, `/run_live` and `/docs`. An app serves only what its
frontend uses: the bricks it names, an allow-list of routes, and nothing that reads a session.

```python
# server.py
SERVED_BRICKS = {"assistant": "agents", "order_lookup": "workflows"}  # name: folder in bricks/
SERVED_ROUTES = {("POST", "/run_sse"), ("GET", "/list-apps"), ("GET", "/health")}
SERVED_PATHS = {path for _, path in SERVED_ROUTES}
MAX_REQUEST = 64 * 1024  # bytes


class Bricks(BaseAgentLoader):
    """Lists and loads only the named bricks, never another folder or importable module."""

    def __init__(self, bricks: Path, served: dict[str, str]):
        self._folders = dict(served)
        self._loaders = {f: AgentLoader(str(bricks / f)) for f in set(served.values())}

    def list_agents(self) -> list[str]:
        return sorted(self._folders)

    def load_agent(self, agent_name: str):
        if agent_name not in self._folders:
            raise ValueError(f"No served brick is named {agent_name}.")  # ADK answers 404
        return self._loaders[self._folders[agent_name]].load_agent(agent_name)


def _served(route: BaseRoute) -> bool:
    methods = getattr(route, "methods", None) or set()
    return any((method, getattr(route, "path", "")) in SERVED_ROUTES for method in methods)


class Gate:
    """Answers before the router: 404 off the allow-list, 413 over the size cap."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":  # none is served (/run_live)
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        method, path = scope["method"], scope["path"]
        static = method in ("GET", "HEAD") and path not in SERVED_PATHS  # the frontend's files
        if (method, path) not in SERVED_ROUTES and not static:
            await _reply(send, 404, "Not Found")
            return
        declared = dict(scope["headers"]).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > MAX_REQUEST:
            await _reply(send, 413, "Request too large")
            return
        received = 0

        async def capped() -> Message:  # a body sent without its length is counted
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_REQUEST:
                    raise HTTPException(413, "Request too large")
            return message

        await self._app(scope, capped, send)


app = get_fast_api_app(
    agents_dir=str(BRICKS / "agents"), agent_loader=Bricks(BRICKS, SERVED_BRICKS),
    web=False, use_local_storage=False, auto_create_session=True,
)
app.router.routes[:] = [route for route in app.router.routes if _served(route)]
app.add_middleware(Gate)
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
```

`_reply` sends a small JSON answer straight to `send`. The lists are configuration, not logic.
A new brick, or a route the frontend starts to call, is served only once it is named here.
Every brick still runs alone with `adk web`.

## Sessions

Decide which of the two the app is.

**It holds a conversation** (the sample: the user picks a brick and keeps talking). Keep ADK's
sessions, as above, and never serve the session routes. With no sign-in every caller has the
same user id, so the session id is all that separates one conversation from another: the
frontend makes an unguessable one per conversation (`crypto.randomUUID()`) and sends it with
each turn. Sessions stay in memory until the process ends.

**Its bricks keep nothing between requests** (each request carries all it needs). Delete each
session when its request ends, with the `user:` and `app:` state ADK keeps outside it, so
nothing a caller sent outlives the answer. The frontend sends a new unguessable session id
(`crypto.randomUUID()`) with every request: two requests under one id would share a session
while both run.

```python
_made: ContextVar[list[tuple[str, str, str]] | None] = ContextVar("made", default=None)


class RequestSessions(InMemorySessionService):
    """Notes the sessions a request creates, so `Stateless` can drop them after it."""

    async def create_session(self, *, app_name, user_id, state=None, session_id=None):
        session = await super().create_session(
            app_name=app_name, user_id=user_id, state=state, session_id=session_id
        )
        if (made := _made.get()) is not None:
            made.append((app_name, user_id, session.id))
        return session


class Stateless(Gate):
    def __init__(self, app: ASGIApp, sessions: InMemorySessionService) -> None:
        super().__init__(app)
        self._sessions = sessions

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        made: list[tuple[str, str, str]] = []
        token = _made.set(made)
        try:
            await super().__call__(scope, receive, send)
        finally:
            _made.reset(token)
            for app_name, user_id, session_id in made:
                await self._sessions.delete_session(
                    app_name=app_name, user_id=user_id, session_id=session_id
                )
                # delete_session leaves the state kept under `user:` and `app:` keys
                self._sessions.user_state.get(app_name, {}).pop(user_id, None)
                self._sessions.app_state.pop(app_name, None)


SESSIONS = RequestSessions()
get_service_registry().register_session_service("request", lambda uri, **kwargs: SESSIONS)
# then: get_fast_api_app(..., session_service_uri="request://")
#       app.add_middleware(Stateless, sessions=SESSIONS)
```

## Build and run

```bash
docker build -f apps/web-sample-1/Dockerfile -t web-sample-1 .
docker run --rm -p 8080:8080 --env-file .env web-sample-1
```

## Traps

- **Build from the repository root,** so the image can copy `bricks/`, `pyproject.toml` and
  `uv.lock`. Install with `uv sync --frozen --no-dev`.
- **Mount the frontend after the API is created,** so ADK's routes win over the static files.
- **Dropping a route is not enough.** The static mount at `/` answers 405 to a POST on any
  path, so refuse by method and path before the router, as `Gate` does. Remove the routes as
  well, so the router holds nothing the list does not.
- **Name the bricks; do not list folders.** A listed folder makes every agent in it callable
  over `/run_sse`, past the limits of the workflow that normally calls it, and ADK's loader
  imports any module name it is given. `""` and `__names` ADK refuses itself (400, 403).
  Name top-level bricks only: a part is reached through its owner (B8), so the sample's app
  names the assistant and not the analyst inside it.
- **A shared user id makes session routes a leak.** `GET /apps/<app>/users/<user>/sessions`
  hands every conversation to any caller. Never serve them without sign-in.
- **Cap the size before parsing.** ADK parses and stores a request of any size. Refuse from
  `Content-Length`, and count the bytes of a body sent without one.
- **Test the app beside `server.py`** with FastAPI's `TestClient` and a scripted model, with
  a frontend folder mounted: the named bricks are listed and run, any other name and every
  other route answer 404, the socket closes, an oversized request answers 413. Ask in review:
  what can a caller reach that the frontend never calls?
- **One port serves both.** The frontend calls `/list-apps` and `/run_sse` on its own origin;
  in development Vite proxies those two paths to the server.
- **Listen on `PORT`,** as Cloud Run sets it.
- **The key never enters the image.** `.env` is in `.dockerignore` and `.gitignore`, and is
  passed at run time.
- **Name an app after the specific output** (`web-sample-1`), not a generic word.

Checked on `google-adk` 2.11.0. The stateless case first ran in an app on 2.10.0. Not proven
here: a Cloud Run deployment, sign-in, and expiring kept sessions. Deploy the image with
`gcloud run deploy`; the `cloud-run-basics` skill in the `gcp-vertex-cloudrun` plugin covers it.
