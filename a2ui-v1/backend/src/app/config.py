import os

from dotenv import load_dotenv

from app.paths import REPO_ROOT

load_dotenv(REPO_ROOT / ".env")  # a2ui-v1/.env (gitignored), see .env.example

MODEL = os.environ.get("A2UI_DEMO_MODEL", "gemini-3.1-flash-lite")
