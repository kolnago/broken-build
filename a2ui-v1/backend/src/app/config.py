import os

from dotenv import load_dotenv

load_dotenv()

MODEL = os.environ.get("A2UI_DEMO_MODEL", "gemini-3.1-flash-lite")
