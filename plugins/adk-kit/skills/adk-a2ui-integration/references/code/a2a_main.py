"""A2A front door with the A2UI extension. Imports and signatures checked against a2ui-agent-sdk
0.7.0, google-adk 2.10.0 (re-verified on 2.11.0) and a2a-sdk 0.3.x (the SDK requires a2a-sdk<0.4)."""

from a2a.types import AgentCapabilities, AgentCard
from a2ui.a2a.extension import get_a2ui_agent_extension  # not re-exported from a2ui.a2a
from a2ui.a2a.parts import create_a2ui_part
from google.adk.a2a.converters.part_converter import convert_genai_part_to_a2a_part
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor, A2aAgentExecutorConfig
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from app.agent import root_agent
from app.config import BASIC_CATALOG_ID

card = AgentCard(
    name="limit_advisor",
    description="Overdraft limit advisor",
    url="https://advisor.internal/a2a",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=True, extensions=[
        # URI https://a2ui.org/a2a-extension/a2ui/v0.9.1; acceptsInlineCatalogs defaults to False
        get_a2ui_agent_extension("0.9.1", supported_catalog_ids=[BASIC_CATALOG_ID])]),
    skills=[],
)


def a2ui_part_converter(part):
    """show_* / emit_ui results become one DataPart per A2UI message (application/a2ui+json);
    everything else goes through ADK's default. ADK's converter alone drops A2UI (adk-python #7308)."""
    fr = part.function_response
    if fr and (fr.response or {}).get("status") == "rendered":
        return [create_a2ui_part(m, version="0.9.1") for m in fr.response["a2ui"]]
    return convert_genai_part_to_a2a_part(part)


# gen_ai_part_converter is used by both of ADK's executor paths. The SDK's A2uiEventConverter is not
# a fit here: it only plugs into the legacy path, only converts send_a2ui_json_to_client results,
# and stamps the deprecated MIME (it builds its part converter with version "0.8").
# Incoming: negotiate with a2ui.a2a.extension.try_activate_a2ui_extension(context, agent_card)
# and route action DataParts to handle_action.
a2a_app = to_a2a(  # uvicorn app.a2a_main:a2a_app
    root_agent,
    agent_card=card,
    agent_executor_factory=lambda runner: A2aAgentExecutor(
        runner=runner, config=A2aAgentExecutorConfig(gen_ai_part_converter=a2ui_part_converter)),
)
