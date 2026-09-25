from google.adk.agents import LlmAgent

from app.config import MODEL

root_agent = LlmAgent(
    name="chat",
    model=MODEL,
    description="Plain text assistant.",
    instruction="You are a helpful, concise assistant. Answer in plain text.",
)
