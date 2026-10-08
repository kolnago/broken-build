"""Production entrypoint: ADK HTTP API without the dev UI (google-adk 2.11).

uvicorn main:app --host 0.0.0.0 --port 8080
"""
import os

from google.adk.cli.fast_api import get_fast_api_app

app = get_fast_api_app(
    agents_dir=os.getenv('AGENTS_DIR', './agents'),   # one package per agent
    web=False,
    session_service_uri=os.getenv('SESSION_URI', 'sqlite:///./sessions.db'),
    artifact_service_uri=os.getenv('ARTIFACT_URI'),     # e.g. gs://bucket
    memory_service_uri=os.getenv('MEMORY_URI'),         # e.g. agentengine://<id>
    use_local_storage=False,
    otel_to_cloud=os.getenv('OTEL_TO_CLOUD') == '1',
    max_llm_calls=int(os.getenv('MAX_LLM_CALLS', '50')),
)


@app.get('/build-info')
async def build_info() -> dict[str, str]:
  return {'commit': os.getenv('GIT_SHA', 'dev')}
