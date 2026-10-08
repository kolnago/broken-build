"""Tests for check_modules.py on small synthetic repositories."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from check_modules import load  # noqa: E402

PYPROJECT = """
[tool.adk_modules]
order = [["breaches.*"], ["investigation"], ["exposure"]]
"""

MODULE_DOC = '"""{name}: what this area of the domain is."""\n'


def write(root: Path, rel: str, text: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def brick(root: Path, rel: str, kind: str, name: str, body: str, init_extra: str = "") -> None:
    """A brick at rel/kind/name with a thin __init__, one implementation file and a test."""
    base = f"{rel}/{kind}/{name}"
    if not (root / rel / kind / "__init__.py").exists():
        write(root, f"{rel}/{kind}/__init__.py")
    write(root, f"{base}/__init__.py",
          f'"""{kind[:-1].title()} brick, strict. In: x. Out: y."""\n'
          f"from .{name} import {name}\n{init_extra}__all__ = ['{name}']\n")
    write(root, f"{base}/{name}.py", body)
    write(root, f"{base}/test_{name}.py", f"from . import {name}\n")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A clean repository: exposure <- investigation <- breaches.limit_overdraft."""
    write(tmp_path, "pyproject.toml", PYPROJECT)
    write(tmp_path, "modules/__init__.py")
    # exposure
    write(tmp_path, "modules/exposure/__init__.py",
          MODULE_DOC.format(name="Exposure") +
          "from .models.money import money\nfrom .calc.pdlc import pdlc\n"
          "from .ports.positions import positions\n__all__ = ['money', 'pdlc', 'positions']\n")
    brick(tmp_path, "modules/exposure", "models", "money", "def money(): ...\n")
    brick(tmp_path, "modules/exposure", "calc", "pdlc", "from modules.exposure.models.money import money\ndef pdlc(): ...\n")
    brick(tmp_path, "modules/exposure", "ports", "positions", "from modules.exposure.models.money import money\ndef positions(): ...\n")
    # investigation
    write(tmp_path, "modules/investigation/__init__.py",
          MODULE_DOC.format(name="Investigation") +
          "from .callbacks.guard import guard\n__all__ = ['guard']\n")
    brick(tmp_path, "modules/investigation", "callbacks", "guard",
          "from modules.exposure import money\ndef guard(): ...\n")
    # breaches group with one module, whose agent has a part
    write(tmp_path, "modules/breaches/__init__.py", '"""Breach types, one module each."""\n')
    write(tmp_path, "modules/breaches/limit_overdraft/__init__.py",
          MODULE_DOC.format(name="Limit overdraft") +
          "from .agents.investigator import investigator\n__all__ = ['investigator']\n")
    brick(tmp_path, "modules/breaches/limit_overdraft", "agents", "investigator",
          "from modules.exposure import pdlc, positions\nfrom modules.investigation import guard\n"
          "from .agents.explainer import explainer\ndef investigator(): ...\n")
    brick(tmp_path, "modules/breaches/limit_overdraft/agents/investigator", "agents", "explainer",
          "def explainer(): ...\n")
    write(tmp_path, "modules/breaches/limit_overdraft/agents/investigator/agent.py",
          "import os\nfrom . import investigator\nroot_agent = investigator()\n")
    # an app and a spike
    write(tmp_path, "apps/risk-manager/server.py", "from modules.breaches.limit_overdraft import investigator\n")
    write(tmp_path, "spikes/__init__.py")
    write(tmp_path, "spikes/idea.py", "from modules.exposure.calc.pdlc.pdlc import pdlc\n")
    return tmp_path


def errors(root: Path) -> list[str]:
    return load(root).check()


def test_clean_repository_passes(repo: Path) -> None:
    assert errors(repo) == []


def test_discovers_modules_groups_and_parts(repo: Path) -> None:
    tree = load(repo)
    tree.discover()
    assert sorted(m.name for m in tree.modules) == ["breaches.limit_overdraft", "exposure", "investigation"]
    assert [g.name for g in tree.groups] == ["breaches"]
    lo = next(m for m in tree.modules if m.name == "breaches.limit_overdraft")
    parts = [b.path.name for b in lo.bricks if b.owner is not None]
    assert parts == ["explainer"]
    exposure = next(m for m in tree.modules if m.name == "exposure")
    assert exposure.exports == {"money": "models", "pdlc": "calc", "positions": "ports"}
    assert exposure.export_sources == {"money": "models.money", "pdlc": "calc.pdlc", "positions": "ports.positions"}


def test_m1_banned_name_and_missing_docstring(repo: Path) -> None:
    write(repo, "modules/common/__init__.py", "from .models.thing import thing\n__all__ = ['thing']\n")
    brick(repo, "modules/common", "models", "thing", "def thing(): ...\n")
    found = errors(repo)
    assert any("M1 'common' is not a domain name" in e for e in found)
    assert any("M1 module __init__.py has no docstring" in e for e in found)
    assert any("M3 'common' is missing from" in e for e in found)


def test_m2_path_import_and_unexported_name(repo: Path) -> None:
    write(repo, "modules/investigation/callbacks/guard/guard.py",
          "from modules.exposure.calc.pdlc import pdlc\nfrom modules.exposure import secret\ndef guard(): ...\n")
    found = errors(repo)
    assert any("M2 imports a path inside module 'exposure'" in e for e in found)
    assert any("M2 'secret' is not exported by module 'exposure'" in e for e in found)


def test_m3_upward_and_same_level_imports(repo: Path) -> None:
    write(repo, "modules/exposure/calc/pdlc/pdlc.py", "from modules.investigation import guard\ndef pdlc(): ...\n")
    found = errors(repo)
    assert any("M3 module 'exposure' imports 'investigation', which is on a higher level" in e for e in found)
    # a sibling in the group, same level
    write(repo, "modules/breaches/concentration/__init__.py",
          MODULE_DOC.format(name="Concentration") + "from .agents.conc import conc\n__all__ = ['conc']\n")
    brick(repo, "modules/breaches/concentration", "agents", "conc",
          "from modules.breaches.limit_overdraft import investigator\ndef conc(): ...\n")
    found = errors(repo)
    assert any("M3 module 'breaches.concentration' imports 'breaches.limit_overdraft', which is on the same level" in e
               for e in found)


def test_m4_kind_order_inside_and_across_modules(repo: Path) -> None:
    write(repo, "modules/exposure/models/money/money.py", "from ...calc.pdlc import pdlc\ndef money(): ...\n")
    found = errors(repo)
    assert any("M4 a model brick imports pdlc from calc/" in e for e in found)
    # across modules: a port importing an exported callback
    write(repo, "modules/breaches/limit_overdraft/__init__.py",
          MODULE_DOC.format(name="LO") + "from .agents.investigator import investigator\n"
          "from .ports.alerts import alerts\n__all__ = ['investigator', 'alerts']\n")
    brick(repo, "modules/breaches/limit_overdraft", "ports", "alerts",
          "from modules.investigation import guard\ndef alerts(): ...\n")
    found = errors(repo)
    assert any("M4 a port brick imports guard from callbacks/" in e for e in found)


def test_m5_group_exports_or_imports_nothing(repo: Path) -> None:
    write(repo, "modules/breaches/__init__.py",
          '"""Breaches."""\nfrom .limit_overdraft import investigator\n__all__ = ["investigator"]\n')
    found = errors(repo)
    assert any("M5 a group's __init__.py imports nothing" in e for e in found)
    assert any("M5 a group's __init__.py exports nothing" in e for e in found)


def test_b3_import_from_file_inside_a_brick(repo: Path) -> None:
    write(repo, "modules/exposure/calc/pdlc/pdlc.py", "from modules.exposure.models.money.money import money\ndef pdlc(): ...\n")
    assert any("B3 imports a file inside brick 'money'" in e for e in errors(repo))


def test_b5_missing_test(repo: Path) -> None:
    (repo / "modules/exposure/calc/pdlc/test_pdlc.py").unlink()
    assert any("B5 brick has no test_*.py" in e for e in errors(repo))


def test_b8_part_imported_from_outside_and_re_exported(repo: Path) -> None:
    write(repo, "modules/breaches/limit_overdraft/agents/intruder/__init__.py",
          '"""Agent brick, free."""\nfrom .intruder import intruder\n__all__ = ["intruder"]\n')
    write(repo, "modules/breaches/limit_overdraft/agents/intruder/intruder.py",
          "from ...agents.investigator.agents.explainer import explainer\ndef intruder(): ...\n")
    write(repo, "modules/breaches/limit_overdraft/agents/intruder/test_intruder.py", "")
    found = errors(repo)
    assert any("B8 imports part 'explainer' of 'investigator' from outside the owner" in e for e in found)
    write(repo, "modules/breaches/limit_overdraft/agents/investigator/__init__.py",
          '"""Agent brick, strict."""\nfrom .investigator import investigator\n'
          "from .agents.explainer import explainer\n__all__ = ['investigator', 'explainer']\n")
    assert any("B8 re-exports part 'explainer'" in e for e in errors(repo))


def test_b9_implementation_in_init(repo: Path) -> None:
    write(repo, "modules/exposure/calc/pdlc/__init__.py",
          '"""Calculator brick, strict."""\ndef pdlc():\n    return 1\n__all__ = ["pdlc"]\n')
    assert any("B9 __init__.py holds implementation (line 2)" in e for e in errors(repo))


def test_b9_allows_get_agent_async(repo: Path) -> None:
    write(repo, "modules/breaches/limit_overdraft/agents/investigator/__init__.py",
          '"""Agent brick, strict."""\nfrom .investigator import investigator\n__all__ = ["investigator"]\n\n'
          "async def get_agent_async():\n    from .agent import root_agent\n    return root_agent, None\n")
    assert not [e for e in errors(repo) if "B9" in e]


def test_spikes_are_isolated(repo: Path) -> None:
    write(repo, "modules/exposure/calc/pdlc/pdlc.py", "from spikes.idea import x\ndef pdlc(): ...\n")
    assert any("SP imports from spikes" in e for e in errors(repo))
    # and a spike may reach inside anything: the clean repo's spike does, with no error
    assert not [e for e in errors(repo) if e.startswith("spikes/")]


def test_apps_use_exports_only(repo: Path) -> None:
    write(repo, "apps/risk-manager/server.py",
          "from modules.breaches.limit_overdraft.agents.investigator import investigator\n")
    assert any(e.startswith("apps/risk-manager/server.py: M2") for e in errors(repo))


def test_m2_m3_module_imported_as_a_name_through_a_parent_package(repo: Path) -> None:
    write(repo, "modules/exposure/calc/pdlc/pdlc.py", "from modules import investigation\ndef pdlc(): ...\n")
    write(repo, "apps/risk-manager/server.py", "from modules.breaches import limit_overdraft\n")
    found = errors(repo)
    assert any("pdlc.py: M2 imports module 'investigation' as a name from 'modules'" in e for e in found)
    assert any("pdlc.py: M3 module 'exposure' imports 'investigation', which is on a higher level" in e for e in found)
    assert any("server.py: M2 imports module 'breaches.limit_overdraft' as a name from 'modules.breaches'" in e
               for e in found)


def test_m4_through_the_modules_own_init(repo: Path) -> None:
    write(repo, "modules/exposure/calc/pdlc/pdlc.py", "from modules.exposure import positions, money\ndef pdlc(): ...\n")
    found = errors(repo)
    assert any("pdlc.py: M4 a calculator brick imports positions from ports/" in e for e in found)
    assert not [e for e in found if "money" in e]
    # the same through a relative import
    write(repo, "modules/exposure/calc/pdlc/pdlc.py", "from ... import positions\ndef pdlc(): ...\n")
    assert any("pdlc.py: M4 a calculator brick imports positions from ports/" in e for e in errors(repo))


def test_m4_exempts_a_bricks_tests(repo: Path) -> None:
    lo = "modules/breaches/limit_overdraft"
    brick(repo, lo, "skills", "lo_method", "def lo_method(): ...\n")
    write(repo, f"{lo}/skills/lo_method/test_lo_method.py",
          f"from {lo.replace('/', '.')}.agents.investigator import investigator\n"
          f"from {lo.replace('/', '.')}.skills.lo_method import lo_method\n")
    write(repo, f"{lo}/skills/lo_method/conftest.py", f"from {lo.replace('/', '.')}.agents.investigator import investigator\n")
    assert not [e for e in errors(repo) if "M4" in e]
    # the brick's code is still held to M4
    write(repo, f"{lo}/skills/lo_method/lo_method.py",
          f"from {lo.replace('/', '.')}.agents.investigator import investigator\ndef lo_method(): ...\n")
    assert any("lo_method.py: M4 a skill brick imports investigator from agents/" in e for e in errors(repo))


def test_unparseable_file_is_reported(repo: Path) -> None:
    write(repo, "modules/exposure/calc/pdlc/pdlc.py", "from modules.investigation import guard\ndef pdlc(:\n")
    found = errors(repo)
    assert found == ["modules/exposure/calc/pdlc/pdlc.py: PARSE cannot be parsed (line 2: invalid syntax); "
                     "nothing in it was checked"]


def test_all_may_be_annotated_or_extended(repo: Path) -> None:
    write(repo, "modules/exposure/__init__.py",
          MODULE_DOC.format(name="Exposure") +
          "from .models.money import money\nfrom .calc.pdlc import pdlc\nfrom .ports.positions import positions\n"
          "__all__: list[str] = ['money', 'pdlc']\n__all__ += ['positions']\n")
    write(repo, "modules/exposure/calc/pdlc/__init__.py",
          '"""Calculator brick, strict."""\nfrom .pdlc import pdlc\n__all__: list[str] = ["pdlc"]\n')
    assert errors(repo) == []
    write(repo, "modules/breaches/__init__.py", '"""Breaches."""\n__all__: list[str] = ["x"]\n')
    assert any("M5 a group's __init__.py exports nothing" in e for e in errors(repo))


def test_b9_allows_a_docstring_in_get_agent_async(repo: Path) -> None:
    write(repo, "modules/breaches/limit_overdraft/agents/investigator/__init__.py",
          '"""Agent brick, strict."""\nfrom .investigator import investigator\n__all__ = ["investigator"]\n\n'
          'async def get_agent_async():\n    """For adk eval."""\n    from .agent import root_agent\n'
          "    return root_agent, None\n")
    assert not [e for e in errors(repo) if "B9" in e]


def test_b3_sibling_part_whose_name_extends_ours(repo: Path) -> None:
    owner = "modules/breaches/limit_overdraft/agents/investigator"
    brick(repo, owner, "agents", "explainer_v2", "def explainer_v2(): ...\n")
    write(repo, f"{owner}/agents/explainer/explainer.py",
          "from ..explainer_v2.explainer_v2 import explainer_v2\ndef explainer(): ...\n")
    assert any("explainer.py: B3 imports a file inside brick 'explainer_v2'" in e for e in errors(repo))


def test_spikes_match_the_package_not_a_prefix(repo: Path) -> None:
    write(repo, "modules/exposure/calc/pdlc/pdlc.py", "import spikesaurus\nfrom spikes_too import x\ndef pdlc(): ...\n")
    assert errors(repo) == []
