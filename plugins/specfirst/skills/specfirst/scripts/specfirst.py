#!/usr/bin/env python3
"""Set up and check the spec-first docs layout (specfirst skill).

    specfirst.py init  [--root DIR]   create docs/ folders, learnings.md, AGENTS.md stub (idempotent)
    specfirst.py check [--root DIR]   validate intents, specs, plans, ADRs and WIP.md; exit 1 on FAIL
    specfirst.py log   [--root DIR] [--trailers]
                                      the application's log: every intent in order, with size, status,
                                      closed by; --trailers cross-checks git's Intent: trailers

Standard library only. `check` is the mechanical half of the gates: it does not judge content,
it checks that artifacts have the shape the guide requires and that WIP.md keeps its fence.
Every file is read and written as UTF-8, whatever the platform default.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DIRS = ["docs/intents", "docs/specs", "docs/plans"]
OPTIONAL_DIRS = ["docs/adr", "docs/evals"]  # ADRs may live in the guide; evals only where there is an agent
TIERS = {"mechanical", "standard", "judgement"}
AUTONOMY = {"show tasks", "run to verify", "autonomous"}
APPROVED_BY = {"human", "ai"}
DELEGATION = {"off", "by tier"}
STATUS = {"draft", "approved", "implemented", "superseded"}
AC_TAGS = {"unit", "contract", "integration", "e2e", "eval", "metric", "manual"}
MAX_TASKS, MAX_FIX_TASKS, MAX_CHECKPOINTS = 10, 3, 2
HASH = r"[0-9a-f]{7,40}"

LEARNINGS = "# Learnings\n\nDated entries, newest first; one per shipped spec (specfirst §3.8).\n"
AGENTS_MD = """# AGENTS.md

Always-on rules for assistants in this repository. The workflow is the `specfirst` skill; the
code rules are this project's architecture guide, named here. Both load when a task needs them.

- Architecture guide: <path or skill name, e.g. `docs/architecture.md`; none yet: start from the specfirst skill's `templates/architecture-guide.md`>
- Done commands: <the project's lint, typecheck, import-rule and test commands, e.g. `make check` or `npm run lint && npm test`>
- ADRs live in: <`docs/adr/` | a section of the architecture guide>
- Autonomy default: <show tasks | run to verify>   (recommended answer at spec approval)
- Delegation: <off | by tier>   (off: the session does every task; by tier: each task runs in a fresh
  subagent on the model its `Tier:` allows, and `WIP.md` carries a `Budget:` line)
- Rule groups not applicable: <none | e.g. STO, SEC-1..3 (no data store, no identity in the app)>
- Every change starts as an intent (`docs/intents/` is the log of the application) and is
  triaged small or large (specfirst §2.2). Large changes go intent → spec → plan → tasks →
  implement → review → verify → learn; artifacts are keyed `I-/S-/P-YYMMDDHHMM-<slug>` (§2.1).
  Every commit under an intent carries the trailer `Intent: I-<key>`.
- `WIP.md` is the fence during a large change. Anything outside it is a proposal, not code.
- Hard stops G1–G9 (specfirst §1.1) end a run: clean tree, one STOP line in the log, wait;
  after the human decides, `resume` adds a RESUME line and continues.
- A large intent may run autonomously when the human answers `go, autonomous` (specfirst §3.9):
  the AI approves its own spec (`Approved by: ai`), works on branch `auto/<key>`, and the human's
  next gate is VERIFY.
- Done is mechanical: the Done commands above, plus
  `python3 <path-to-specfirst-skill>/scripts/specfirst.py check`.
"""


class Report:
    def __init__(self) -> None:
        self.fails: list[str] = []
        self.warns: list[str] = []
        self.oks: list[str] = []
        self.next: list[str] = []

    def fail(self, msg: str) -> None:
        self.fails.append(msg)

    def warn(self, msg: str) -> None:
        self.warns.append(msg)

    def ok(self, msg: str) -> None:
        self.oks.append(msg)

    def print(self) -> int:
        if self.next:
            print("Next:")
            for n in self.next:
                print(f"  {n}")
            print()
        for m in self.oks:
            print(f"ok    {m}")
        for m in self.warns:
            print(f"warn  {m}")
        for m in self.fails:
            print(f"FAIL  {m}")
        print(f"\n{len(self.oks)} ok, {len(self.warns)} warnings, {len(self.fails)} failures")
        return 1 if self.fails else 0


# ---------------------------------------------------------------- files


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- init


def cmd_init(root: Path) -> int:
    for d in DIRS + OPTIONAL_DIRS:
        p = root / d
        if p.is_dir():
            print(f"exists   {d}/")
        else:
            p.mkdir(parents=True)
            (p / ".gitkeep").touch()
            print(f"created  {d}/")
    learnings = root / "docs" / "learnings.md"
    if learnings.exists():
        print("exists   docs/learnings.md")
    else:
        write(learnings, LEARNINGS)
        print("created  docs/learnings.md")
    agents = root / "AGENTS.md"
    if not agents.exists():
        write(agents, AGENTS_MD)
        print("created  AGENTS.md (stub; name the architecture guide and the path to specfirst.py)")
    elif "specfirst" not in read(agents):
        print("exists   AGENTS.md — it does not mention specfirst; add a section like:\n")
        print("\n".join("    " + line for line in AGENTS_MD.splitlines()[2:]))
    else:
        print("exists   AGENTS.md")
    print("\nNot created: WIP.md (belongs to a change, not the project; see templates/wip.md).")
    return 0


# ---------------------------------------------------------------- helpers


def field(text: str, name: str) -> str | None:
    m = re.search(rf"^{re.escape(name)}:\s*(.*?)\s*$", text, re.M)
    return m.group(1) if m else None


def heading_id(text: str, prefix: str) -> str | None:
    m = re.search(rf"^#\s+({prefix}-[\w.…-]+)", text, re.M)
    return m.group(1) if m else None


def section(text: str, heading: str, level: int = 2) -> str:
    """The body of `## heading` (or `###`), up to the next heading of the same or higher level."""
    hashes = "#" * level
    m = re.search(rf"^{hashes}\s+{re.escape(heading)}\b.*$", text, re.M | re.I)
    if not m:
        return ""
    rest = text[m.end():]
    end = re.search(rf"^#{{1,{level}}}\s", rest, re.M)
    return rest[: end.start()] if end else rest


def artifacts(root: Path, sub: str, prefix: str) -> list[Path]:
    d = root / "docs" / sub
    return sorted(p for p in d.glob(f"{prefix}-*.md")) if d.is_dir() else []


def agents_setting(root: Path, name: str) -> str:
    """`<name>: value` from AGENTS.md, without a trailing parenthesis or comment; '' when unset."""
    agents = root / "AGENTS.md"
    if not agents.exists():
        return ""
    m = re.search(rf"^-?\s*{re.escape(name)}:\s*`?([^`\n(]*)", read(agents), re.M)
    value = m.group(1).strip() if m else ""
    return "" if value.startswith("<") else value


def check_common(rep: Report, p: Path, text: str, prefix: str, rel: str, need_derived: bool = True) -> None:
    hid = heading_id(text, prefix)
    if not hid:
        rep.fail(f"{rel}: first heading must be `# {prefix}-<id> <title>`")
    elif hid != p.stem:
        rep.fail(f"{rel}: heading ID `{hid}` does not match file name `{p.stem}`")
    if need_derived and not field(text, "Derived from"):
        rep.fail(f"{rel}: missing `Derived from:` line")


# ---------------------------------------------------------------- git


def git(root: Path, *args: str) -> str | None:
    """stdout of a git command, or None when git is missing, this is not a repository, or it fails."""
    try:
        return subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def clean(value: str | None) -> str:
    return (value or "").split("<!--")[0].strip()


def current_branch(root: Path) -> str | None:
    out = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return out.strip() if out is not None else None


def commit_exists(root: Path, commit: str) -> bool | None:
    """None when git cannot answer (no git, no repository)."""
    if git(root, "rev-parse", "--is-inside-work-tree") is None:
        return None
    return git(root, "cat-file", "-e", f"{commit}^{{commit}}") is not None


def commit_trailer(root: Path, commit: str) -> str | None:
    """The `Intent:` trailer value of a commit; '' when it has none; None when git cannot answer."""
    body = git(root, "show", "-s", "--format=%B", commit)
    if body is None:
        return None
    m = re.search(r"^Intent:\s*(I-\S+)\s*$", body, re.M)
    return m.group(1) if m else ""


def _sections(text: str | None) -> list[str]:
    """The `## ` section each line (1-based index) lies in; a heading belongs to its own section."""
    out, cur = [""], ""
    for line in (text or "").splitlines():
        if line.startswith("## "):
            cur = line[3:].strip().lower()
        out.append(cur)
    return out


def _is_real_edit(root: Path, commit: str, path: Path) -> bool:
    """A later commit is a real edit of a spec unless it changes the `Version:` line (a bump) or
    every line it changes is the `Status:` line (e.g. the commit that records `implemented
    <hash>`), a line under `## Change requests`, or a blank line (VFY-4)."""
    diff = git(root, "show", "--format=", "-U0", commit, "--", str(path)) or ""
    before = _sections(git(root, "show", f"{commit}^:./{path}"))
    after = _sections(git(root, "show", f"{commit}:./{path}"))
    changed: list[tuple[str, str]] = []  # (line, section it lies in)
    old = new = 0
    for line in diff.splitlines():
        h = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if h:
            old, new = int(h.group(1)), int(h.group(2))
        elif old and line[:1] == "-":
            changed.append((line[1:], before[old] if old < len(before) else ""))
            old += 1
        elif new and line[:1] == "+":
            changed.append((line[1:], after[new] if new < len(after) else ""))
            new += 1
    if any(line.startswith("Version:") for line, _ in changed):
        return False
    return not all(
        line.startswith("Status:") or not line.strip() or sec.startswith("change requests")
        for line, sec in changed
    )


def git_commits_after(root: Path, commit: str, path: Path) -> list[str] | None:
    """Commits after `commit` that really edit `path` (see `_is_real_edit`)."""
    out = git(root, "log", "--format=%h", f"{commit}..HEAD", "--", str(path))
    if out is None:
        return None
    return [c for c in out.split() if _is_real_edit(root, c, path)]


# ---------------------------------------------------------------- check: pieces


def ac_blocks(text: str) -> list[str]:
    """Acceptance criteria as blocks: `AC-1 …`, `- **AC-1** …`, `| AC-1 |`, continued until the next AC, blank line or heading."""
    m = re.search(r"^##\s+Acceptance criteria.*$", text, re.M | re.I)
    if m:  # only the section that defines them; evidence tables elsewhere also start with AC-n
        end = re.search(r"^##\s", text[m.end():], re.M)
        text = text[m.end(): m.end() + end.start()] if end else text[m.end():]
    lines = text.splitlines()
    blocks, cur = [], None
    for line in lines:
        if re.match(r"^\s*(?:[-*]\s*)?(?:\*\*)?AC-\d+(?:\*\*)?[\s:]+(?!and\b|or\b)", line):
            if cur: blocks.append(" ".join(cur))
            cur = [line.strip()]
        elif cur is not None and (line.strip() == "" or line.startswith("#")):
            blocks.append(" ".join(cur)); cur = None
        elif cur is not None:
            cur.append(line.strip())
    if cur: blocks.append(" ".join(cur))
    return blocks


def ac_ids(blocks: list[str]) -> list[str]:
    return [m.group(0) for b in blocks for m in [re.search(r"AC-\d+", b)] if m]


def ac_tags(block: str) -> set[str]:
    groups = re.findall(r"\(([^()]*)\)", block)
    # a tag may carry words after it: `(integration, with fakes)`, `(manual review)`
    return {(tok.split() or [""])[0].lower() for g in groups for tok in re.split(r"[,;/]", g)}


def excluded_rules(root: Path) -> list[str]:
    """`Rule groups not applicable:` from AGENTS.md as regexes: `DATA` → `DATA-\\d+`, `SEC-1..3` → SEC-1|2|3."""
    value = agents_setting(root, "Rule groups not applicable")
    if not value or value.lower().startswith("none"):
        return []
    out: list[str] = []
    for tok in re.findall(r"[A-Z]{2,5}(?:-\d+(?:\.\.\d+)?)?", value):
        m = re.match(r"([A-Z]{2,5})-(\d+)\.\.(\d+)$", tok)
        if m:
            nums = "|".join(str(n) for n in range(int(m.group(2)), int(m.group(3)) + 1))
            out.append(rf"\b{m.group(1)}-(?:{nums})\b")
        elif "-" in tok:
            out.append(rf"\b{re.escape(tok)}\b")
        else:
            out.append(rf"\b{tok}-\d+")
    return out


def closing_hashes(text: str) -> list[str]:
    """The commit hashes on the `Closed by:` line; a `<placeholder>` counts as none."""
    m = re.search(r"^\*\*Closed by:\*\*\s*(\S.*)$", text, re.M)
    if not m or m.group(1).strip().startswith("<"):
        return []
    return re.findall(rf"\b{HASH}\b", m.group(1))


def check_intent(rep: Report, root: Path, p: Path, text: str, specs: dict[str, str]) -> None:
    rel = str(p.relative_to(root))
    check_common(rep, p, text, "I", rel, need_derived=False)
    for h in ("Raw intent", "Structured intent", "Open questions", "Triage"):
        if not re.search(rf"^##\s+{h}\b", text, re.M):
            rep.fail(f"{rel}: missing `## {h}` section")
    hashes = closing_hashes(text)
    if not hashes and "S-" + p.stem[2:] not in specs:
        rep.warn(f"{rel}: open (no Closed by, no spec)")
    for h in hashes:  # the closing commits exist and say which intent they close
        exists = commit_exists(root, h)
        if exists is None:
            break
        if not exists:
            rep.warn(f"{rel}: Closed by {h} is not a commit in this repository")
            continue
        trailer = commit_trailer(root, h)
        if trailer is not None and trailer != p.stem:
            rep.warn(f"{rel}: Closed by {h} carries no `Intent: {p.stem}` trailer (got `{trailer or 'none'}`)")


def check_spec(rep: Report, root: Path, p: Path, text: str, default_autonomy: str, excluded: list[str]) -> tuple[str, list[str]]:
    rel = str(p.relative_to(root))
    check_common(rep, p, text, "S", rel)
    status = (field(text, "Status") or "").strip()
    status_word = status.split()[0] if status else ""
    if status_word not in STATUS or "|" in status:
        rep.fail(f"{rel}: `Status:` must be one of {sorted(STATUS)} (got `{status}`)")
    version = field(text, "Version") or ""
    if not version.isdigit():
        rep.fail(f"{rel}: `Version:` must be an integer (got `{version}`)")
    aut = clean(field(text, "Autonomy"))
    by = clean(field(text, "Approved by"))
    if status_word == "approved":
        if aut not in AUTONOMY and not default_autonomy:
            rep.fail(f"{rel}: approved spec needs `Autonomy: show tasks | run to verify | autonomous`, or an `Autonomy default:` in AGENTS.md (got `{aut}`)")
    if status_word in {"approved", "implemented"}:
        if by and by not in APPROVED_BY:
            rep.fail(f"{rel}: `Approved by:` must be `human` or `ai` (got `{by}`)")
        if aut == "autonomous" and by != "ai":
            rep.fail(f"{rel}: `Autonomy: autonomous` needs `Approved by: ai` (AUTO-1)")
        elif by == "ai" and aut != "autonomous":
            rep.fail(f"{rel}: `Approved by: ai` is only valid with `Autonomy: autonomous` (AUTO-1)")
        if aut == "autonomous" and not re.search(r"^Assumptions made:", text, re.M):
            rep.warn(f"{rel}: autonomous spec has no `Assumptions made:` list (AUTO-2)")
    if status_word in {"approved", "implemented"} and not re.search(r"^##\s+Read-back", text, re.M):
        rep.fail(f"{rel}: approved spec has no `## Read-back` (SPEC-5)")
    acs = ac_blocks(text)
    if not acs:
        rep.fail(f"{rel}: no acceptance criteria (`AC-1 …`) found (SPEC-1)")
    for ac in acs:
        if not ac_tags(ac) & AC_TAGS:
            rep.fail(f"{rel}: `{ac[:40]}…` needs a tag in {sorted(AC_TAGS)}, as prefix or suffix (SPEC-1)")
    applies = section(text, "Rules that apply").split("Not applicable", 1)[0]
    for pattern in excluded:
        hit = re.search(pattern, applies)
        if hit:
            rep.warn(f"{rel}: Rules that apply cites `{hit.group(0)}`, a group AGENTS.md lists as not applicable")
    if status_word == "implemented":
        m = re.search(rf"implemented\s+(?:\(|commit\s*)?({HASH})", status)
        if not m:
            rep.warn(f"{rel}: implemented spec should record the commit hash (VFY-4)")
        else:
            after = git_commits_after(root, m.group(1), p.relative_to(root))
            if after:
                rep.warn(f"{rel}: changed after implemented commit {m.group(1)} ({len(after)} commits); bump Version or supersede")
    return status_word, ac_ids(acs)


def check_plan(rep: Report, root: Path, p: Path, text: str, specs: dict[str, str], keyed: re.Pattern[str], legacy: list[str]) -> str | None:
    rel = str(p.relative_to(root))
    check_common(rep, p, text, "P", rel)
    for h in ("Touched layers", "Rule exceptions", "New dependencies", "Deferred"):
        if not re.search(rf"^##\s+{h}\b", text, re.M):
            rep.fail(f"{rel}: missing `## {h}` section (PLAN-1/2/3/5)")
    d = field(text, "Derived from") or ""
    m = re.search(r"\b(S-[A-Za-z0-9_-]+)", d)
    spec_id = None
    if m:
        spec_id = m.group(1)
        if keyed.match(p.stem[2:]) and spec_id != "S-" + p.stem[2:]:
            rep.fail(f"{rel}: plan key `{p.stem[2:]}` must equal its spec's key `{spec_id[2:]}` (NAME-3)")
        elif not keyed.match(p.stem[2:]):
            legacy.append(p.stem)
        if spec_id not in specs:
            rep.fail(f"{rel}: derived from `{spec_id}` which does not exist")
    if not re.search(r"\b(P\d+|[A-Z]{2,5}-\d+)\b", text.split("## Touched layers", 1)[-1][:2000]):
        rep.warn(f"{rel}: no rule IDs found under Touched layers (PLAN-1)")
    return spec_id


def check_review(rep: Report, text: str) -> None:
    """A verdict without the fence map and the AC map is an opinion (REV-2)."""
    review = section(text, "Review")
    if not re.search(r"^-\s*Verdict:", review, re.M):
        return
    for line in ("Fence:", "Spec:"):
        if not re.search(rf"^-\s*{line}", review, re.M):
            rep.fail(f"WIP.md Review: has a verdict but no `- {line}` line (REV-2: a clean verdict shows what was mapped)")


def check_verify(rep: Report, text: str, acs: list[str], spec_status: str, all_ticked: bool) -> None:
    """Every AC of the spec has an evidence row once the spec is implemented (VFY-1)."""
    verify = section(text, "Verify")
    rows = {m.group(1): m.group(2) for m in re.finditer(r"^-\s*(AC-\d+)\s+(.*)$", verify, re.M)}
    if spec_status == "implemented":
        for ac in acs:
            if ac not in rows:
                rep.fail(f"WIP.md Verify: no evidence row for {ac} of an implemented spec (VFY-1)")
        for ac, row in rows.items():
            if row.lower().startswith("manual") and not re.search(r"\d{4}-\d{2}-\d{2}", row):
                rep.fail(f"WIP.md Verify: {ac} is manual; its row must say who checked it and when (a date) (VFY-1)")
    elif all_ticked and not rows and acs:
        rep.warn("WIP.md: all tasks ticked and no `## Verify` rows yet (VERIFY stage writes one per AC)")


def check_wip(rep: Report, root: Path, text: str, specs: dict[str, str], spec_acs: dict[str, list[str]], delegation: str,
              autonomous: frozenset[str] | set[str] = frozenset()) -> str | None:
    idle = not re.search(r"^- \[[ xX]\] (?:T|R)\d+\b", text, re.M)
    m = re.match(r"#\s+WIP\s+[—-]+\s+(S-[A-Za-z0-9_-]+)\s+v(\d+)\s*/\s*(P-[A-Za-z0-9_-]+)", text)
    wip_spec = None
    if idle and not m:
        rep.ok("WIP.md: idle (no change in progress, no tasks)")
    elif not m:
        rep.fail("WIP.md: header must be `# WIP — S-<key> v<n> / P-<key>`, or no tasks while idle")
    else:
        wip_spec = m.group(1)
        if wip_spec not in specs:
            rep.fail(f"WIP.md: spec `{wip_spec}` does not exist")
        elif specs[wip_spec] not in {"approved", "implemented"}:
            rep.fail(f"WIP.md: spec `{wip_spec}` is `{specs[wip_spec]}`, not approved")
        if not (root / "docs" / "plans" / f"{m.group(3)}.md").exists():
            rep.fail(f"WIP.md: plan `{m.group(3)}` does not exist")
    tasks = re.findall(r"^- \[([ xX])\] ((?:T|R)\d+)\b(.*)$", text, re.M)
    open_tasks = {t[1] for t in tasks if not t[0].strip()}
    if open_tasks and delegation == "by tier" and not field(text, "Budget"):
        rep.fail("WIP.md: missing `Budget:` line (G8 run budget; Delegation: by tier)")
    t_ids = [t[1] for t in tasks if t[1].startswith("T")]
    r_ids = [t[1] for t in tasks if t[1].startswith("R")]
    if len(t_ids) > MAX_TASKS:
        rep.fail(f"WIP.md: {len(t_ids)} tasks, cap is {MAX_TASKS} (G8: split the scope)")
    if len(r_ids) > MAX_FIX_TASKS:
        rep.fail(f"WIP.md: {len(r_ids)} review fix tasks, more than {MAX_FIX_TASKS} is G8")
    dup = {i for i in t_ids + r_ids if (t_ids + r_ids).count(i) > 1}
    if dup:
        rep.fail(f"WIP.md: duplicate task IDs {sorted(dup)}")
    # per-task block: from the task line to the next task/heading/checkpoint
    tiers: dict[str, str] = {}
    blocks = re.split(r"(?m)^(?=- \[[ xX]\] (?:T|R)\d+\b|## |⏸)", text)
    for b in blocks:
        mm = re.match(r"- \[[ xX]\] ((?:T|R)\d+)", b)
        if not mm:
            continue
        tid = mm.group(1)
        tier = re.search(r"^\s*Tier:\s*(\S.*?)\s*$", b, re.M)
        if tier:
            tiers[tid] = tier.group(1)
        if tid not in open_tasks:
            continue  # ticked tasks are history; the fence is checked on what is still to do
        if not tier:
            rep.fail(f"WIP.md {tid}: missing `Tier:` (TASK-7)")
        elif tier.group(1) not in TIERS:
            rep.fail(f"WIP.md {tid}: Tier `{tier.group(1)}` not in {sorted(TIERS)}")
        if not re.search(r"^\s*Checks:\s*\S", b, re.M):
            rep.fail(f"WIP.md {tid}: missing `Checks:` (TASK-2)")
    cps = re.findall(r"^⏸\s*CHECKPOINT\b(.*)$", text, re.M)
    if len(cps) > MAX_CHECKPOINTS:
        rep.fail(f"WIP.md: {len(cps)} checkpoints, cap is {MAX_CHECKPOINTS} (TASK-6)")
    for cp in cps:
        w = re.search(r"waits on:\s*(\S.*)$", cp)
        if w and open_tasks:
            rep.next.append(f"WIP.md: parked at a checkpoint that waits on {w.group(1).strip()}")
    if "## Log" not in text and not idle:
        rep.fail("WIP.md: missing `## Log` section")
    log = section(text, "Log")
    commits: dict[str, list[str]] = {}
    for done, tid, _ in tasks:
        if not done.strip():
            continue
        line = re.search(rf"^-\s*(?:\S+\s+)?{tid}\b.*$", log, re.M)
        if not line:
            rep.fail(f"WIP.md {tid}: ticked but no log line starting with `- {tid}` (TASK-5)")
            continue
        model = re.search(r"\bmodel=(\S+)", line.group(0))
        if delegation == "by tier" and model and model.group(1) == "session" and tiers.get(tid) in {"mechanical", "standard"}:
            rep.warn(f"WIP.md {tid}: Tier {tiers[tid]} but model=session; Delegation is by tier (IMPL-6)")
        for h in re.findall(rf"\bcommit=({HASH})\b", line.group(0)):
            commits.setdefault(h, []).append(tid)
    for h, tids in commits.items():
        if len(tids) > 1:
            rep.warn(f"WIP.md: {', '.join(tids)} share commit {h}; one task, one commit (§3.5)")
        exists = commit_exists(root, h)
        if exists is False:
            rep.warn(f"WIP.md {tids[0]}: log names commit {h}, which is not in this repository")
    # a STOP is resolved by a later RESUME for the same task; only the open ones need a person
    open_stops: dict[str, str] = {}
    for line in re.findall(r"^-\s*(?:STOP|RESUME)\b.*$", log, re.M):
        ev = re.match(r"-\s*(STOP|RESUME)\s+((?:T|R)\d+)?", line)
        kind, tid = ev.group(1), ev.group(2) or "?"
        if kind == "STOP":
            open_stops[tid] = line.strip()
        elif tid in open_stops:
            rep.ok(f"WIP.md: resumed — {open_stops.pop(tid)[2:]}")
    for line in open_stops.values():
        rep.warn(f"WIP.md: {line}")
    if wip_spec in autonomous and not idle and specs.get(wip_spec) != "implemented":
        want = "auto/" + wip_spec[2:]
        branch = current_branch(root)
        if branch is not None and branch != want:
            rep.warn(f"WIP.md: autonomous run for {wip_spec} should be on branch `{want}` (AUTO-3), current is `{branch}`")
    if "## Review" not in text and not idle:
        rep.warn("WIP.md: no `## Review` section yet (REVIEW stage writes it)")
    check_review(rep, text)
    if wip_spec:
        check_verify(rep, text, spec_acs.get(wip_spec, []), specs.get(wip_spec, ""), bool(tasks) and not open_tasks)
    rep.ok(f"WIP.md: {len(t_ids)} tasks ({sum(1 for d, _, _ in tasks if d.strip())} ticked), {len(r_ids)} fix tasks, {len(cps)} checkpoints")
    return wip_spec


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{5,}", text.lower())}


def learnings_follow_ups(root: Path, intents: list[str]) -> list[str]:
    """Follow-up lines in learnings.md that no intent picks up (half of their longer words unseen)."""
    p = root / "docs" / "learnings.md"
    if not p.exists():
        return []
    open_lines: list[str] = []
    for m in re.finditer(r"^Follow-ups\b.*$", read(p), re.M):
        rest = read(p)[m.end():]
        block = rest.split("\n\n", 1)[0]
        for line in re.findall(r"^-\s*(.*)$", block, re.M):
            words = _words(line)
            if not words:
                continue
            if not any(len(words & _words(text)) * 2 >= len(words) for text in intents):
                open_lines.append(line.strip())
    return open_lines


# ---------------------------------------------------------------- check


def cmd_check(root: Path) -> int:
    rep = Report()
    default_autonomy = agents_setting(root, "Autonomy default")
    delegation = agents_setting(root, "Delegation") or "off"
    if delegation not in DELEGATION:
        rep.warn(f"AGENTS.md: `Delegation:` should be one of {sorted(DELEGATION)} (got `{delegation}`); treating it as off")
        delegation = "off"
    excluded = excluded_rules(root)
    if (root / "AGENTS.md").exists() and not agents_setting(root, "Done commands"):
        rep.warn("AGENTS.md: no `Done commands:` (the project's lint, typecheck, import-rule and test commands); Done is undefined (§1 rule 7)")
    missing = [d for d in DIRS if not (root / d).is_dir()]
    if missing:
        rep.fail(f"missing folders: {', '.join(missing)} (run `specfirst.py init`)")
    if not (root / "docs" / "learnings.md").exists():
        rep.warn("docs/learnings.md missing (LEARN stage writes here)")

    specs: dict[str, str] = {}
    spec_acs: dict[str, list[str]] = {}
    autonomous: set[str] = set()
    for p in artifacts(root, "specs", "S"):
        text = read(p)
        specs[p.stem], spec_acs[p.stem] = check_spec(rep, root, p, text, default_autonomy, excluded)
        if clean(field(text, "Autonomy")) == "autonomous":
            autonomous.add(p.stem)
    intent_texts: list[str] = []
    for p in artifacts(root, "intents", "I"):
        text = read(p)
        intent_texts.append(text)
        check_intent(rep, root, p, text, specs)
    # keyed naming (NAME-1..3): timestamped keys must chain intent → spec → plan
    keyed = re.compile(r"^\d{10}-[a-z0-9]+(?:-[a-z0-9]+){0,4}$")
    intent_keys = {p.stem[2:] for p in artifacts(root, "intents", "I")}
    legacy: list[str] = []
    for p in artifacts(root, "intents", "I"):
        key = p.stem[2:]
        if re.match(r"^\d{10}-", key) and not keyed.match(key):
            rep.fail(f"docs/intents/{p.name}: slug must be lowercase ASCII kebab-case, at most five words (NAME-1)")
        elif not keyed.match(key):
            legacy.append(p.stem)
    for sid in specs:
        key = sid[2:]
        if keyed.match(key):
            if key not in intent_keys:
                rep.warn(f"docs/specs/{sid}.md: no docs/intents/I-{key}.md — a spec takes its intent's key (NAME-3); pre-adoption specs may lack one")
        else:
            legacy.append(sid)
    plans: dict[str, str] = {}
    for p in artifacts(root, "plans", "P"):
        sid = check_plan(rep, root, p, read(p), specs, keyed, legacy)
        if sid:
            plans[sid] = p.stem
    if legacy:
        rep.warn(f"{len(legacy)} artifact(s) with legacy sequential IDs ({', '.join(sorted(legacy)[:4])}{'…' if len(legacy) > 4 else ''}); new chains use I-/S-/P-YYMMDDHHMM-<slug> (NAME-1..3)")
    for p in artifacts(root, "adr", "ADR"):
        rel, text = str(p.relative_to(root)), read(p)
        check_common(rep, p, text, "ADR", rel, need_derived=False)
        st = (field(text, "Status") or "").strip()
        if not st or "|" in st:
            rep.fail(f"{rel}: `Status:` must be set (proposed | accepted | superseded by …)")
    wip = root / "WIP.md"
    wip_spec = check_wip(rep, root, read(wip), specs, spec_acs, delegation, autonomous) if wip.exists() else None

    # what's next
    for sid, st in specs.items():
        if st == "approved" and sid not in plans:
            rep.next.append(f"{sid}: approved, no plan → `Plan {sid}`")
        elif st == "approved" and sid in plans and wip_spec != sid:
            rep.next.append(f"{sid}: planned ({plans[sid]}), no WIP.md → `Cut tasks for {plans[sid]}`")
    if wip_spec and wip.exists():
        tasks = re.findall(r"^- \[([ xX])\] ((?:T|R)\d+)", read(wip), re.M)
        open_t = [t for d, t in tasks if not d.strip()]
        if open_t or specs.get(wip_spec) != "implemented":
            rep.next.append(f"WIP.md ({wip_spec}): {'all ticked → REVIEW / VERIFY' if not open_t else 'next task ' + open_t[0]}")
    for line in learnings_follow_ups(root, intent_texts):
        rep.next.append(f"learnings follow-up not yet an intent: {line[:90]}")
    rep.ok(f"{len(specs)} specs, {len(plans)} plans checked")
    return rep.print()


# ---------------------------------------------------------------- log


def cmd_log(root: Path, trailers: bool = False) -> int:
    """Every intent in key order with size, status and what closed it."""
    specs = {p.stem: (field(read(p), "Status") or "").split()[0:1] for p in artifacts(root, "specs", "S")}
    rows = []
    for p in artifacts(root, "intents", "I"):
        text = read(p)
        title = (heading_id(text, "I") and re.search(r"^#\s+I-\S+\s+(.*)$", text, re.M)) or None
        size = (re.search(r"^\*\*Size:\*\*\s*(\w+)", text, re.M) or [None, "?"])[1]
        if re.search(r"^\*\*Autonomy:\*\*\s*autonomous", text, re.M):
            size += "/auto"
        closed = (re.search(r"^\*\*Closed by:\*\*\s*(\S.*)$", text, re.M) or [None, ""])[1].strip()
        if closed.startswith("<"):
            closed = ""
        sid = "S-" + p.stem[2:]
        if sid in specs:
            status = f"spec {specs[sid][0] if specs[sid] else '?'}"
        elif closed:
            status = "closed"
        else:
            status = "open"
        rows.append((p.stem, size, status, closed or "—", title.group(1) if title else ""))
    if not rows:
        print("no intents yet"); return 0
    w = max(len(r[0]) for r in rows)
    for key, size, status, closed, title in rows:
        print(f"{key:<{w}}  {size:<11} {status:<18} {closed:<12} {title}")
    print(f"\n{len(rows)} intents: {sum(r[2]=='open' for r in rows)} open, {sum(r[2]=='closed' for r in rows)} closed, {sum(r[2].startswith('spec') for r in rows)} with a spec")
    if trailers:
        return log_trailers(root)
    return 0


def log_trailers(root: Path) -> int:
    """Commits whose `Intent:` trailer names no intent file, and closing commits without the trailer."""
    out = git(root, "log", "--no-merges", "--format=%h%x00%(trailers:key=Intent,valueonly)")
    if out is None:
        print("\n(git is not available here; trailers not checked)")
        return 0
    intents = {p.stem: read(p) for p in artifacts(root, "intents", "I")}
    print("\nTrailers:")
    orphans = 0
    for line in out.splitlines():
        h, _, key = line.partition("\x00")
        key = key.strip()
        if key and key not in intents:
            orphans += 1
            print(f"  {h}: Intent: {key} names no docs/intents/{key}.md")
    missing = 0
    for stem, text in intents.items():
        for h in closing_hashes(text):
            if commit_trailer(root, h) not in (None, stem):
                missing += 1
                print(f"  {stem}: Closed by {h} carries no `Intent: {stem}` trailer")
    if not orphans and not missing:
        print("  every trailer names an intent file; every closing commit carries its trailer")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["init", "check", "log"])
    ap.add_argument("--root", default=".", help="project root (default: current directory)")
    ap.add_argument("--trailers", action="store_true", help="log: cross-check git's Intent: trailers")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    if a.command == "log":
        return cmd_log(root, trailers=a.trailers)
    return {"init": cmd_init, "check": cmd_check}[a.command](root)


if __name__ == "__main__":
    sys.exit(main())
