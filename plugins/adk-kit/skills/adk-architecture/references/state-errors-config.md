# ADK architecture guide v2.0 — §10–12 State and identity, error handling, composition root and configuration

Part of the guide split by section. Rule summary and file index: [../SKILL.md](../SKILL.md); overview, principles and layers: [overview.md](overview.md).

---

## 10. State, identity, and sessions

- **SEC-1** The API layer authenticates the caller and writes identity and entitlement scope into session state before each run.
- **SEC-2** Nodes and tools read identity from context. It never comes from model output or tool arguments.
- **SEC-3** Services enforce entitlements in addition to any row-level security in the data platform.
- **SEC-4** Send the model only what it needs: figure views, not raw positions.
- **SEC-5** State prefixes are deliberate: `temp:` for the ledger and retry counters, `user:` for user-level defaults, unprefixed for session lifetime, `app:` for app-wide values. Keys are constants in `workflows/shell/keys.py`.

---

## 11. Error handling

- **ERR-1** Catch only specific, expected exceptions. Broad `except Exception` in nodes or tools interferes with ADK retry and human-in-the-loop handling.
- **ERR-2** Domain errors map to `status: error` dicts in tools and to routes in workflows, via `DomainError.user_message`.
- **ERR-3** Infrastructure failures propagate; retries are configured at the workflow level.

---

## 12. Composition root and configuration

- **CFG-1** All settings via `pydantic-settings` in `config.py`: model names, dataset identifiers, query limits, retry counts, warn thresholds. No `os.environ` reads elsewhere.
- **CFG-2** `container.py` builds clients → repositories → services → tools → agent → shell with cached factories.
- **CFG-3** `agents/<name>/agent.py` exposes `root_agent` from the container, and `app`, an `App` wrapping it. Only `App` carries plugins, `resumability_config`, context caching and event compaction, and the ADK CLI loads `app` before `root_agent` (google-adk 2.11.0; details in the `adk-app-runtime` skill). `app.name` equals the agent folder name. Tests never use the container.

```python
# agents/analyst/agent.py
from google.adk import Agent                                  # verified: google-adk 2.8.0
from google.adk.apps import App                               # google-adk 2.11.0, see adk-app-runtime
from app import container
from app.tools.derive import build_derive_tool
from app.tools.limit_tools import build_limit_tools
from app.tools.trend_tools import build_trend_tools
from app.workflows.common.prompts import load_prompt
from app.workflows.shell.graph import build_shell

_settings = container.settings()
analyst = Agent(
    name="analyst",
    model=_settings.models.analyst,
    instruction=load_prompt(__package__, "analyst.md"),
    tools=[*build_limit_tools(container.limit_service()),
           *build_trend_tools(container.trend_service()),
           *build_derive_tool()],
)
root_agent = build_shell(analyst, _settings)
app = App(name="analyst", root_agent=root_agent)             # plugins, resumability_config go here
```
