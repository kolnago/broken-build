"""Lets the tests import the adk-workflows examples package and helpers."""
import pathlib
import sys

_here = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
sys.path.insert(0, str(_here.parent.parent / 'adk-workflows'))
