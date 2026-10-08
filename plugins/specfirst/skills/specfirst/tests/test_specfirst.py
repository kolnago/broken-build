"""Tests for scripts/specfirst.py: temporary projects and git repositories, standard library only.

    pytest plugins/python-kit/skills/specfirst/tests
"""

from __future__ import annotations

import importlib.util
import io
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "specfirst.py"
spec = importlib.util.spec_from_file_location("specfirst", SCRIPT)
assert spec and spec.loader
sf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sf)

KEY = "2609111020-limit-breaches"
GIT = shutil.which("git")


# ---------------------------------------------------------------- fixtures


INTENT = f"""# I-{KEY} Explain limit breaches
<!-- key -->

## Raw intent
risk managers keep asking why a portfolio got flagged.

### Clarifications
- Q1 → All desks.

### Context
- Attached: a screenshot of the dashboard.

## Structured intent
**Read as:** A question the agent answers in chat.

## Open questions
- none

## Triage
**Size:** large
**Reason:** New behaviour.
**Next artifact:** S-{KEY}
**Closed by:**
"""

SPEC = f"""# S-{KEY} Limit breach explanation
Derived from: docs/intents/I-{KEY}.md
Status: approved
Version: 1
Autonomy: show tasks

## Read-back
The intent restated.

## Behaviour
Given a portfolio, explain the breach.

## Rules that apply
P1, CORE-6, DATA-3, SEC-2.
Not applicable: figures.

## Acceptance criteria
AC-1  A breached portfolio names one contributor. (unit)
AC-2  A person likes the wording. (manual)

## Not in scope
Collateral.
"""

PLAN = f"""# P-{KEY} Plan for S-{KEY} v1
Derived from: docs/specs/S-{KEY}.md v1

## Touched layers
core/calc  new: trend — CORE-6

## Decisions
D1

## New dependencies
None.

## Rule exceptions
None.

## External repositories
None.

## Risks
R1

## Deferred
"""

WIP = f"""# WIP — S-{KEY} v1 / P-{KEY}
Autonomy: show tasks
Rules: architecture guide §1.1.
Done means: pytest.
Mode: run-to-completion.

- [x] T1 core/calc: trend.
      Tier: judgement
      Checks: unit.
- [ ] T2 core/services: TrendService.
      Tier: standard
      Checks: unit with fakes.
⏸ CHECKPOINT — human reviews; waits on: kolnago/claude-plugins#7

## Proposals (not authorised)

## Review

## Verify

## Log
- T1 done 2026-09-11 tier=judgement model=session checks=unit commit=a1b2c3d — done.
"""

AGENTS = """# AGENTS.md
- Done commands: `make check`
- Autonomy default: show tasks
- Delegation: off
- Rule groups not applicable: DATA, SEC-1..3 (no data store, no identity)
- Done is mechanical: specfirst.py check
"""


def project(tmp_path: Path, *, wip: str | None = WIP, agents: str = AGENTS, spec: str = SPEC) -> Path:
    root = tmp_path / "proj"
    if root.exists():
        shutil.rmtree(root)  # a test may build the project more than once
    for d in ("docs/intents", "docs/specs", "docs/plans"):
        (root / d).mkdir(parents=True)
    (root / "docs/learnings.md").write_text("# Learnings\n", encoding="utf-8")
    (root / "AGENTS.md").write_text(agents, encoding="utf-8")
    (root / f"docs/intents/I-{KEY}.md").write_text(INTENT, encoding="utf-8")
    (root / f"docs/specs/S-{KEY}.md").write_text(spec, encoding="utf-8")
    (root / f"docs/plans/P-{KEY}.md").write_text(PLAN, encoding="utf-8")
    if wip is not None:
        (root / "WIP.md").write_text(wip, encoding="utf-8")
    return root


def check(root: Path) -> tuple[int, str]:
    out = io.StringIO()
    with redirect_stdout(out):
        code = sf.cmd_check(root)
    return code, out.getvalue()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout.strip()


def git_repo(root: Path) -> None:
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")


def commit(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "--short", "HEAD")


needs_git = pytest.mark.skipif(GIT is None, reason="git is not on PATH")


# ---------------------------------------------------------------- init


def test_init_creates_the_layout_once(tmp_path: Path) -> None:
    out = io.StringIO()
    with redirect_stdout(out):
        assert sf.cmd_init(tmp_path) == 0
        assert sf.cmd_init(tmp_path) == 0
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Delegation: <off | by tier>" in agents
    assert "Rule groups not applicable:" in agents
    assert (tmp_path / "docs/learnings.md").exists()
    assert out.getvalue().count("created  AGENTS.md") == 1


# ---------------------------------------------------------------- a well-formed project


def test_well_formed_project_passes(tmp_path: Path) -> None:
    code, out = check(project(tmp_path))
    assert code == 0, out
    assert "FAIL" not in out
    assert "parked at a checkpoint that waits on kolnago/claude-plugins#7" in out


def test_missing_intent_section_fails(tmp_path: Path) -> None:
    root = project(tmp_path)
    p = root / f"docs/intents/I-{KEY}.md"
    p.write_text(p.read_text(encoding="utf-8").replace("## Triage", "## Sizing"), encoding="utf-8")
    code, out = check(root)
    assert code == 1 and "missing `## Triage` section" in out


def test_files_are_read_as_utf8_whatever_the_locale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """S8: an arrow in Clarifications must not depend on the platform encoding."""
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")
    root = project(tmp_path)
    p = root / f"docs/intents/I-{KEY}.md"
    assert "→" in p.read_bytes().decode("utf-8")
    code, out = check(root)
    assert code == 0, out


# ---------------------------------------------------------------- S11: excluded rule groups


def test_spec_citing_an_excluded_rule_group_warns(tmp_path: Path) -> None:
    code, out = check(project(tmp_path))
    assert code == 0
    assert "cites `DATA-3`, a group AGENTS.md lists as not applicable" in out
    assert "cites `SEC-2`" in out
    assert "CORE-6" not in out


# ---------------------------------------------------------------- S2: review map lines


def test_verdict_without_map_lines_fails(tmp_path: Path) -> None:
    wip = WIP.replace("## Review\n", "## Review\n- Verdict: clean\n- Model: x\n")
    code, out = check(project(tmp_path, wip=wip))
    assert code == 1
    assert "has a verdict but no `- Fence:` line" in out
    assert "has a verdict but no `- Spec:` line" in out


def test_verdict_with_map_lines_passes(tmp_path: Path) -> None:
    review = "## Review\n- Fence: T1 ← core/calc/trend.py\n- Rules read: §1.1\n- Spec: AC-1 ← test_trend\n- Verdict: clean\n- Model: x\n"
    code, out = check(project(tmp_path, wip=WIP.replace("## Review\n", review)))
    assert code == 0, out


# ---------------------------------------------------------------- S3: verify rows


def test_implemented_spec_needs_an_evidence_row_per_ac(tmp_path: Path) -> None:
    spec = SPEC.replace("Status: approved", "Status: implemented a1b2c3d")
    wip = WIP.replace("- [ ] T2", "- [x] T2").replace("## Log\n", "## Log\n- T2 done 2026-09-11 tier=standard model=session checks=unit commit=b2c3d4e — done.\n")
    code, out = check(project(tmp_path, wip=wip, spec=spec))
    assert code == 1
    assert "no evidence row for AC-1 of an implemented spec" in out
    assert "no evidence row for AC-2" in out
    rows = "## Verify\n- AC-1  unit: test_trend\n- AC-2  manual: the reviewer checked it on 2026-09-12 on b2c3d4e, wording fine\n"
    code, out = check(project(tmp_path, wip=wip.replace("## Verify\n", rows), spec=spec))
    assert code == 0, out
    undated = rows.replace(" on 2026-09-12", "")
    code, out = check(project(tmp_path, wip=wip.replace("## Verify\n", undated), spec=spec))
    assert code == 1 and "AC-2 is manual; its row must say who checked it and when" in out


def test_all_ticked_without_verify_rows_warns(tmp_path: Path) -> None:
    wip = WIP.replace("- [ ] T2", "- [x] T2").replace("## Log\n", "## Log\n- T2 done 2026-09-11 tier=standard model=session checks=unit commit=b2c3d4e — done.\n")
    code, out = check(project(tmp_path, wip=wip))
    assert code == 0
    assert "all tasks ticked and no `## Verify` rows yet" in out


# ---------------------------------------------------------------- S1: delegation


def test_budget_is_required_only_when_delegating_by_tier(tmp_path: Path) -> None:
    code, out = check(project(tmp_path))
    assert code == 0 and "Budget" not in out
    code, out = check(project(tmp_path, agents=AGENTS.replace("Delegation: off", "Delegation: by tier")))
    assert code == 1 and "missing `Budget:` line" in out


def test_delegated_tier_that_ran_on_the_session_warns(tmp_path: Path) -> None:
    wip = WIP.replace("Mode:", "Budget: 20 subagent runs.\nMode:").replace("Tier: judgement", "Tier: mechanical")
    agents = AGENTS.replace("Delegation: off", "Delegation: by tier")
    code, out = check(project(tmp_path, wip=wip, agents=agents))
    assert code == 0
    assert "T1: Tier mechanical but model=session; Delegation is by tier" in out


def test_missing_or_unfilled_done_commands_warns(tmp_path: Path) -> None:
    code, out = check(project(tmp_path))
    assert "Done commands" not in out
    for agents in (AGENTS.replace("- Done commands: `make check`\n", ""),
                   AGENTS.replace("`make check`", "<the project's lint and test commands>")):
        code, out = check(project(tmp_path / str(len(agents)), agents=agents))
        assert code == 0
        assert "AGENTS.md: no `Done commands:`" in out


def test_unknown_delegation_value_warns_and_means_off(tmp_path: Path) -> None:
    code, out = check(project(tmp_path, agents=AGENTS.replace("Delegation: off", "Delegation: sometimes")))
    assert code == 0 and "`Delegation:` should be one of" in out


# ---------------------------------------------------------------- S10: shared commits


def test_two_ticked_tasks_sharing_a_commit_warn(tmp_path: Path) -> None:
    wip = WIP.replace("- [ ] T2", "- [x] T2").replace("## Log\n", "## Log\n- T2 done 2026-09-11 tier=standard model=session checks=unit commit=a1b2c3d — with T1.\n")
    code, out = check(project(tmp_path, wip=wip))
    assert code == 0
    assert "T1, T2 share commit a1b2c3d; one task, one commit" in out


# ---------------------------------------------------------------- S7: git cross-checks


@needs_git
def test_closed_by_and_log_commits_are_checked_against_git(tmp_path: Path) -> None:
    root = project(tmp_path, wip=None)
    git_repo(root)
    good = commit(root, f"Do it\n\nIntent: I-{KEY}")
    (root / "x.txt").write_text("x", encoding="utf-8")
    bare = commit(root, "No trailer")
    p = root / f"docs/intents/I-{KEY}.md"
    p.write_text(p.read_text(encoding="utf-8").replace("**Closed by:**", f"**Closed by:** {good}, {bare}, 0000000"), encoding="utf-8")
    code, out = check(root)
    assert code == 0
    assert f"Closed by {bare} carries no `Intent: I-{KEY}` trailer" in out
    assert "Closed by 0000000 is not a commit in this repository" in out
    assert f"Closed by {good}" not in out


@needs_git
def test_log_commit_missing_from_git_warns(tmp_path: Path) -> None:
    root = project(tmp_path)
    git_repo(root)
    commit(root, f"Start\n\nIntent: I-{KEY}")
    code, out = check(root)
    assert code == 0
    assert "log names commit a1b2c3d, which is not in this repository" in out


@needs_git
def test_log_trailers_reports_both_directions(tmp_path: Path) -> None:
    root = project(tmp_path, wip=None)
    git_repo(root)
    orphan = commit(root, "Orphan\n\nIntent: I-2609111021-nothing")
    (root / "y.txt").write_text("y", encoding="utf-8")
    bare = commit(root, "Bare")
    p = root / f"docs/intents/I-{KEY}.md"
    p.write_text(p.read_text(encoding="utf-8").replace("**Closed by:**", f"**Closed by:** {bare}"), encoding="utf-8")
    out = io.StringIO()
    with redirect_stdout(out):
        assert sf.cmd_log(root, trailers=True) == 0
    text = out.getvalue()
    assert f"{orphan}: Intent: I-2609111021-nothing names no docs/intents" in text
    assert f"I-{KEY}: Closed by {bare} carries no" in text


# ---------------------------------------------------------------- real edits after implemented (0.1.3)


@needs_git
def test_only_real_edits_count_after_implemented(tmp_path: Path) -> None:
    root = project(tmp_path, wip=None)
    git_repo(root)
    first = commit(root, f"Implement\n\nIntent: I-{KEY}")
    spec_path = root / f"docs/specs/S-{KEY}.md"
    spec_path.write_text(SPEC.replace("Status: approved", f"Status: implemented {first}"), encoding="utf-8")
    commit(root, "Status only")
    code, out = check(root)
    assert "changed after implemented" not in out
    spec_path.write_text(spec_path.read_text(encoding="utf-8").replace("Collateral.", "Collateral, intraday."), encoding="utf-8")
    commit(root, "Body edit")
    code, out = check(root)
    assert f"changed after implemented commit {first} (1 commits)" in out



@needs_git
def test_change_requests_after_implemented_are_not_real_edits(tmp_path: Path) -> None:
    root = project(tmp_path, wip=None)
    git_repo(root)
    first = commit(root, f"Implement\n\nIntent: I-{KEY}")
    spec_path = root / f"docs/specs/S-{KEY}.md"
    spec_path.write_text(SPEC.replace("Status: approved", f"Status: implemented {first}"), encoding="utf-8")
    commit(root, "Status only")
    with spec_path.open("a", encoding="utf-8") as f:
        f.write("\n## Change requests\n- CR-1 Name two contributors when they tie.\n")
    commit(root, "Change request")
    with spec_path.open("a", encoding="utf-8") as f:
        f.write("- CR-2 Show the limit as well.\n")
    commit(root, "Another change request")
    code, out = check(root)
    assert "changed after implemented" not in out
    spec_path.write_text(spec_path.read_text(encoding="utf-8").replace("Collateral.", "Collateral, intraday."), encoding="utf-8")
    commit(root, "Body edit")
    code, out = check(root)
    assert f"changed after implemented commit {first} (1 commits)" in out

# ---------------------------------------------------------------- learnings follow-ups


def test_learnings_follow_up_without_an_intent_is_listed(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / "docs/learnings.md").write_text(
        "# Learnings\n\n## 2026-09-27 S-x\n- note\n\nFollow-ups (proposals):\n"
        "- Smoke run: print each set's kind so reviewers see last sets directly.\n"
        "- Explain limit breaches to risk managers when a portfolio got flagged.\n",
        encoding="utf-8",
    )
    code, out = check(root)
    assert code == 0
    assert "learnings follow-up not yet an intent: Smoke run: print each set's kind" in out
    assert "Explain limit breaches" not in out  # the intent above covers it


# ---------------------------------------------------------------- idle WIP


def test_idle_wip_passes(tmp_path: Path) -> None:
    code, out = check(project(tmp_path, wip="# WIP\nIdle since S-x.\n"))
    assert code == 0 and "WIP.md: idle" in out


def test_main_runs_check_and_log(tmp_path: Path) -> None:
    root = project(tmp_path)
    out = io.StringIO()
    with redirect_stdout(out):
        assert sf.main(["check", "--root", str(root)]) == 0
        assert sf.main(["log", "--root", str(root)]) == 0
    assert f"I-{KEY}" in out.getvalue()
    sys.stdout.flush()


# ---------------------------------------------------------------- §3.9: autonomous run

AUTO_SPEC = SPEC.replace("Autonomy: show tasks", "Autonomy: autonomous\nApproved by: ai").replace(
    "The intent restated.\n", "The intent restated.\n\nAssumptions made:\n- A1 all desks, as the intent says.\n"
)


def test_autonomous_spec_approved_by_ai_passes(tmp_path: Path) -> None:
    code, out = check(project(tmp_path, spec=AUTO_SPEC))
    assert code == 0, out
    assert "AUTO-" not in out


def test_autonomy_and_approved_by_must_agree(tmp_path: Path) -> None:
    code, out = check(project(tmp_path, spec=AUTO_SPEC.replace("Approved by: ai", "Approved by: human")))
    assert code == 1 and "`Autonomy: autonomous` needs `Approved by: ai` (AUTO-1)" in out
    code, out = check(project(tmp_path, spec=SPEC.replace("Autonomy: show tasks", "Autonomy: show tasks\nApproved by: ai")))
    assert code == 1 and "`Approved by: ai` is only valid with `Autonomy: autonomous` (AUTO-1)" in out
    code, out = check(project(tmp_path, spec=SPEC.replace("Autonomy: show tasks", "Autonomy: show tasks\nApproved by: robot")))
    assert code == 1 and "`Approved by:` must be `human` or `ai`" in out


def test_autonomous_spec_without_assumptions_warns(tmp_path: Path) -> None:
    spec = AUTO_SPEC.replace("Assumptions made:\n- A1 all desks, as the intent says.\n", "")
    code, out = check(project(tmp_path, spec=spec))
    assert code == 0 and "autonomous spec has no `Assumptions made:` list (AUTO-2)" in out


def test_resume_resolves_a_stop(tmp_path: Path) -> None:
    stop = "- STOP T2 2026-09-11 G3 — needs a new dependency.\n"
    code, out = check(project(tmp_path, wip=WIP + stop))
    assert code == 0 and "warn  WIP.md: - STOP T2 2026-09-11 G3" in out
    code, out = check(project(tmp_path, wip=WIP + stop + "- RESUME T2 2026-09-12 — human allowed it.\n"))
    assert code == 0
    assert "resumed — STOP T2 2026-09-11 G3" in out
    assert "warn  WIP.md: - STOP" not in out


@needs_git
def test_autonomous_run_belongs_on_its_auto_branch(tmp_path: Path) -> None:
    root = project(tmp_path, spec=AUTO_SPEC)
    git_repo(root)
    commit(root, "start")
    git(root, "checkout", "-q", "-b", "elsewhere")
    code, out = check(root)
    assert code == 0 and f"should be on branch `auto/{KEY}` (AUTO-3), current is `elsewhere`" in out
    git(root, "checkout", "-q", "-b", f"auto/{KEY}")
    code, out = check(root)
    assert code == 0 and "AUTO-3" not in out


def test_log_marks_an_autonomous_intent(tmp_path: Path) -> None:
    root = project(tmp_path)
    p = root / f"docs/intents/I-{KEY}.md"
    p.write_text(p.read_text(encoding="utf-8").replace("**Size:** large", "**Size:** large\n**Autonomy:** autonomous"), encoding="utf-8")
    out = io.StringIO()
    with redirect_stdout(out):
        assert sf.cmd_log(root) == 0
    assert "large/auto" in out.getvalue()
