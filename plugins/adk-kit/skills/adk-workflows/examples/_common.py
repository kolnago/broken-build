"""Shared helpers for the ADK 2.x examples (google-adk >= 2.11).

MODEL is read from ADK_MODEL so the same files run against Gemini in dev and
against a fake model in tests.
"""
import os

MODEL = os.getenv('ADK_MODEL', 'gemini-2.5-flash')
