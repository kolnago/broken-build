#!/usr/bin/env python3
"""Check the adk-modules charter's contracts that a linter cannot.

Usage: python scripts/check_modules.py [REPO_ROOT]

Reads `[tool.adk_modules]` from pyproject.toml (`order`, optional `modules`, `apps`, `spikes`)
and checks the source tree:

  M1  a module is not named common/shared/core/utils and its __init__.py has a docstring
  M2  across modules, imports name the module only and only what its __all__ exports
  M3  modules import only downward along the declared order; every module is in the order
  M4  inside a module, kinds import inward (models <- calc, ports <- tools <- agents ...);
      a brick's tests (test_*.py, conftest.py) may import any kind
  M5  a group's __init__.py exports nothing and imports nothing
  B3  inside a module, a brick is imported from its package, not from a file inside it
  B5  every brick has a test_*.py beside its code
  B8  a part is imported only by its owner and the owner's other parts, never re-exported
  B9  a brick's __init__.py holds only its docstring, imports and __all__
  SP  nothing outside spikes/ imports from spikes
  PARSE  a file that cannot be parsed is reported, since nothing in it could be checked

Exit status 1 when anything is violated. Standard library only; Python 3.11+.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KINDS: dict[str, set[str]] = {  # kind -> kinds it may import (M4)
    "models": {"models"},
    "ports": {"models"},
    "calc": {"models", "calc"},
    "fakes": {"models"},
    "skills": {"models"},
    "callbacks": {"models", "calc"},
    "surfaces": {"models", "calc"},
    "tools": {"models", "ports", "calc", "surfaces"},
    "mcp": {"models", "ports", "calc", "tools"},
    "agents": set(),  # empty = any kind
    "workflows": set(),
}
SINGULAR: dict[str, str] = {  # kind folder -> the brick it holds, for messages
    "models": "model", "ports": "port", "calc": "calculator", "fakes": "fake", "skills": "skill",
    "callbacks": "callback", "surfaces": "surface", "tools": "tool", "mcp": "MCP server",
    "agents": "agent", "workflows": "workflow",
}
BANNED_MODULE_NAMES = {"common", "shared", "core", "utils", "util", "helpers", "misc", "lib"}
ENTRY_POINTS = {"agent.py", "__main__.py"}
INIT_FUNCTIONS = {"get_agent_async"}  # the one function B9 allows in an __init__.py


@dataclass
class Brick:
    path: Path
    module: "Module"
    kind: str
    owner: Brick | None = None  # set when this brick is a part (B8)

    @property
    def dotted(self) -> str:
        return self.module.tree.dotted(self.path)

    @property
    def top_owner(self) -> Brick:
        return self if self.owner is None else self.owner.top_owner


@dataclass
class Module:
    path: Path
    tree: "Tree"
    bricks: list[Brick] = field(default_factory=list)
    exports: dict[str, str | None] = field(default_factory=dict)  # name -> kind it came from
    export_sources: dict[str, str] = field(default_factory=dict)  # name -> "calc.pdlc"

    @property
    def dotted(self) -> str:
        return self.tree.dotted(self.path)

    @property
    def name(self) -> str:  # relative to the modules root: "breaches.limit_overdraft"
        return ".".join(self.path.relative_to(self.tree.modules_root).parts)


@dataclass
class Tree:
    root: Path
    modules_root: Path
    apps_root: Path
    spikes_root: Path
    order: list[list[str]]
    modules: list[Module] = field(default_factory=list)
    groups: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    asts: dict[Path, ast.Module] = field(default_factory=dict)

    def dotted(self, path: Path) -> str:
        return ".".join(path.relative_to(self.root).with_suffix("").parts)

    def fail(self, where: Path, rule: str, message: str) -> None:
        self.errors.append(f"{where.relative_to(self.root)}: {rule} {message}")

    def parse(self, py: Path) -> ast.Module:
        """The file's syntax tree; a file that cannot be read or parsed is reported once."""
        if py not in self.asts:
            try:
                self.asts[py] = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            except SyntaxError as exc:
                self.fail(py, "PARSE", f"cannot be parsed (line {exc.lineno}: {exc.msg}); "
                          "nothing in it was checked")
                self.asts[py] = ast.Module(body=[], type_ignores=[])
            except OSError as exc:
                self.fail(py, "PARSE", f"cannot be read ({exc.strerror}); nothing in it was checked")
                self.asts[py] = ast.Module(body=[], type_ignores=[])
        return self.asts[py]

    # ----- discovery -------------------------------------------------------------------------

    def discover(self) -> None:
        if not self.modules_root.is_dir():
            self.fail(self.root, "M1", f"no {self.modules_root.name}/ folder")
            return
        for child in _packages(self.modules_root):
            self._classify(child)
        for module in self.modules:
            self._collect_bricks(module, module.path, None)
            module.exports, module.export_sources = _exports(module.path / "__init__.py", self)

    def _classify(self, path: Path) -> None:
        kind_children = [c for c in _packages(path) if c.name in KINDS]
        if kind_children:
            self.modules.append(Module(path, self))
            return
        children = _packages(path)
        if not children:
            self.fail(path, "M1", "is neither a module (no kind folders) nor a group (no modules)")
            return
        self.groups.append(path)
        for child in children:
            self._classify(child)

    def _collect_bricks(self, module: Module, parent: Path, owner: Brick | None) -> None:
        for kind_dir in _packages(parent):
            if kind_dir.name not in KINDS:
                continue
            for brick_dir in _packages(kind_dir):
                brick = Brick(brick_dir, module, kind_dir.name, owner)
                module.bricks.append(brick)
                self._collect_bricks(module, brick_dir, brick)

    # ----- lookups ---------------------------------------------------------------------------

    def module_of(self, path: Path) -> Module | None:
        for module in sorted(self.modules, key=lambda m: -len(m.path.parts)):
            if path.is_relative_to(module.path):
                return module
        return None

    def module_by_dotted(self, dotted: str) -> Module | None:
        for module in sorted(self.modules, key=lambda m: -len(m.dotted)):
            if _is_or_under(dotted, module.dotted):
                return module
        return None

    def brick_of(self, path: Path) -> Brick | None:
        module = self.module_of(path)
        if module is None:
            return None
        for brick in sorted(module.bricks, key=lambda b: -len(b.path.parts)):
            if path.is_relative_to(brick.path):
                return brick
        return None

    def brick_by_dotted(self, dotted: str) -> Brick | None:
        module = self.module_by_dotted(dotted)
        if module is None:
            return None
        for brick in sorted(module.bricks, key=lambda b: -len(b.dotted)):
            if _is_or_under(dotted, brick.dotted):
                return brick
        return None

    def level(self, module: Module) -> int | None:
        name = module.name
        for index, names in enumerate(self.order):
            for pattern in names:
                if pattern == name or (pattern.endswith(".*") and name.startswith(pattern[:-1])):
                    return index
        return None

    # ----- checks ----------------------------------------------------------------------------

    def check(self) -> list[str]:
        self.discover()
        for module in self.modules:
            self._check_module(module)
            for brick in module.bricks:
                self._check_brick(brick)
        for group in self.groups:
            self._check_group(group)
        for py in self._all_sources():
            self._check_imports(py)
        return self.errors

    def _check_module(self, module: Module) -> None:
        if module.path.name in BANNED_MODULE_NAMES:
            self.fail(module.path, "M1", f"'{module.path.name}' is not a domain name")
        init = module.path / "__init__.py"
        if ast.get_docstring(self.parse(init)) is None:
            self.fail(init, "M1", "module __init__.py has no docstring saying what the area is")
        if self.level(module) is None:
            self.fail(module.path, "M3", f"'{module.name}' is missing from [tool.adk_modules] order")

    def _check_group(self, group: Path) -> None:
        init = group / "__init__.py"
        for node in self.parse(init).body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self.fail(init, "M5", "a group's __init__.py imports nothing")
            if _assigns_all(node) and _all_names(node):
                self.fail(init, "M5", "a group's __init__.py exports nothing")

    def _check_brick(self, brick: Brick) -> None:
        if not any(brick.path.glob("test_*.py")):
            self.fail(brick.path, "B5", "brick has no test_*.py beside its code")
        init = brick.path / "__init__.py"
        for node in self.parse(init).body:
            if not _allowed_in_init(node):
                self.fail(init, "B9", f"__init__.py holds implementation (line {node.lineno}); "
                          "move it to a file named by what it contains")
            if brick.owner is None and isinstance(node, ast.ImportFrom) and node.level == 1:
                # re-export of a part: `from .agents.analyst import ...` in the owner's __init__
                target = brick.path.joinpath(*(node.module or "").split("."))
                part = self.brick_of(target) if target.exists() else None
                if part is not None and part is not brick and part.owner is brick:
                    self.fail(init, "B8", f"re-exports part '{part.path.name}'")

    def _check_imports(self, py: Path) -> None:
        if py.is_relative_to(self.spikes_root):
            return  # spikes are outside the rules
        source_module = self.module_of(py)
        source_brick = self.brick_of(py)
        for target, names in _imports(py, self):
            if _is_or_under(target, self.dotted(self.spikes_root)):
                self.fail(py, "SP", f"imports from spikes ({target})")
                continue
            target_module = self.module_by_dotted(target)
            if target_module is None:
                if _is_or_under(target, self.dotted(self.modules_root)):
                    # `from modules import exposure`, `from modules.breaches import limit_overdraft`:
                    # the names are modules, imported through the modules root or a group
                    self._check_module_names(py, source_module, target, names)
                continue  # stdlib, third party, apps: not ours to judge
            if source_module is None or target_module is not source_module:
                self._check_cross_module(py, source_module, target_module, target, names)
            else:
                self._check_within_module(py, source_module, source_brick, target, names)

    def _check_module_names(self, py: Path, source: Module | None, package: str,
                            names: list[str]) -> None:
        for name in names:
            module = self.module_by_dotted(f"{package}.{name}")
            if module is None or module is source:
                continue
            self.fail(py, "M2", f"imports module '{module.name}' as a name from '{package}'; "
                      f"import what the module exports instead (from {module.dotted} import ...)")
            self._check_cross_module(py, source, module, module.dotted, [])

    def _check_cross_module(self, py: Path, source: Module | None, target: Module, dotted: str,
                            names: list[str]) -> None:
        if dotted != target.dotted:
            self.fail(py, "M2", f"imports a path inside module '{target.name}' ({dotted}); "
                      "import what the module exports instead")
        for name in names:
            if name not in target.exports:
                self.fail(py, "M2", f"'{name}' is not exported by module '{target.name}'")
        if source is None:  # apps and spikes are not in the order
            return
        source_level, target_level = self.level(source), self.level(target)
        if source_level is None or target_level is None:
            return  # reported by _check_module
        if target_level <= source_level:
            relation = "the same level" if target_level == source_level else "a higher level"
            self.fail(py, "M3", f"module '{source.name}' imports '{target.name}', which is on "
                      f"{relation} of the order")
        source_brick = self.brick_of(py)
        if source_brick is not None:
            for name in names:
                kind = target.exports.get(name)
                if kind is not None:
                    self._check_kind(py, source_brick.kind, kind, name)

    def _check_within_module(self, py: Path, module: Module, source_brick: Brick | None,
                             dotted: str, names: list[str]) -> None:
        if dotted == module.dotted:
            # `from modules.exposure import positions` inside exposure: judge the brick behind
            # each exported name as if it had been imported directly
            for name in names:
                source = module.export_sources.get(name)
                brick = self.brick_by_dotted(f"{module.dotted}.{source}") if source else None
                if brick is not None:
                    self._check_within_module(py, module, source_brick, brick.dotted, [])
            return
        target_brick = self.brick_by_dotted(dotted)
        if target_brick is None:
            return  # a kind folder
        if source_brick is not None and source_brick.top_owner is target_brick.top_owner \
                and (source_brick is target_brick or _is_or_under(dotted, source_brick.dotted)):
            return  # inside one brick, anything goes
        if dotted != target_brick.dotted:
            self.fail(py, "B3", f"imports a file inside brick '{target_brick.path.name}' ({dotted}); "
                      "import the brick's package")
        if target_brick.owner is not None:
            owner = target_brick.owner
            inside_owner = py.is_relative_to(owner.path)
            if not inside_owner:
                self.fail(py, "B8", f"imports part '{target_brick.path.name}' of "
                          f"'{owner.path.name}' from outside the owner")
        if source_brick is not None:
            self._check_kind(py, source_brick.kind, target_brick.kind, target_brick.path.name)

    def _check_kind(self, py: Path, source_kind: str, target_kind: str, what: str) -> None:
        if _is_test(py):
            return  # a brick's test wires fakes and the owner agent around the brick
        allowed = KINDS[source_kind]
        if allowed and target_kind not in allowed:
            self.fail(py, "M4", f"a {SINGULAR[source_kind]} brick imports {what} from {target_kind}/; "
                      f"{source_kind} may import only {', '.join(sorted(allowed))}")

    def _all_sources(self) -> list[Path]:
        roots = [r for r in (self.modules_root, self.apps_root, self.spikes_root) if r.is_dir()]
        return [p for r in roots for p in sorted(r.rglob("*.py"))]


# ----- helpers -------------------------------------------------------------------------------

def _packages(path: Path) -> list[Path]:
    return sorted(c for c in path.iterdir() if c.is_dir() and (c / "__init__.py").is_file())


def _is_or_under(dotted: str, package: str) -> bool:
    """True when `dotted` is `package` or a module inside it (`spikes.idea`, not `spikesaurus`)."""
    return dotted == package or dotted.startswith(package + ".")


def _is_test(py: Path) -> bool:
    return py.name.startswith("test_") or py.name == "conftest.py"


def _assigns_all(node: ast.stmt) -> bool:
    """`__all__ = [...]`, `__all__: list[str] = [...]` or `__all__ += [...]`."""
    if isinstance(node, ast.Assign):
        return any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
    if isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        return isinstance(node.target, ast.Name) and node.target.id == "__all__"
    return False


def _all_names(node: ast.stmt) -> list[str]:
    if not _assigns_all(node) or not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return []
    value = node.value
    if not isinstance(value, (ast.List, ast.Tuple)):
        return []
    return [e.value for e in value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]


def _is_docstring(node: ast.stmt) -> bool:
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
        and isinstance(node.value.value, str)


def _allowed_in_init(node: ast.stmt) -> bool:
    if _is_docstring(node):
        return True
    if isinstance(node, (ast.Import, ast.ImportFrom)) or _assigns_all(node):
        return True
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in INIT_FUNCTIONS:
        body = node.body[1:] if node.body and _is_docstring(node.body[0]) else node.body
        return all(isinstance(n, (ast.Import, ast.ImportFrom, ast.Return)) for n in body)
    return False


def _exports(init: Path, tree: Tree) -> tuple[dict[str, str | None], dict[str, str]]:
    """The module's __all__ names, each mapped to the kind it came from and to its source
    relative to the module (`calc.pdlc`)."""
    origin: dict[str, str | None] = {}
    sources: dict[str, str] = {}
    for node in tree.parse(init).body:
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            kind = node.module.split(".")[0]
            for alias in node.names:
                origin[alias.asname or alias.name] = kind if kind in KINDS else None
                sources[alias.asname or alias.name] = node.module
    names: list[str] = []
    for node in tree.parse(init).body:
        names += _all_names(node)
    return ({name: origin.get(name) for name in names},
            {name: sources[name] for name in names if name in sources})


def _resolve(py: Path, tree: Tree, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    base = py.parent
    for _ in range(node.level - 1):
        base = base.parent
    if not base.is_relative_to(tree.root):
        return None
    dotted = tree.dotted(base)
    return f"{dotted}.{node.module}" if node.module else dotted


def _imports(py: Path, tree: Tree) -> list[tuple[str, list[str]]]:
    """(dotted target, imported names) for every import in the file; relative ones made absolute."""
    targets: list[tuple[str, list[str]]] = []
    for node in ast.walk(tree.parse(py)):
        if isinstance(node, ast.Import):
            targets += [(alias.name, []) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve(py, tree, node)
            if resolved:
                targets.append((resolved, [alias.name for alias in node.names]))
    return targets


def load(root: Path) -> Tree:
    config: dict[str, Any] = {}
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        config = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {}).get("adk_modules", {})
    return Tree(
        root=root,
        modules_root=root / config.get("modules", "modules"),
        apps_root=root / config.get("apps", "apps"),
        spikes_root=root / config.get("spikes", "spikes"),
        order=config.get("order", []),
    )


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    errors = load(root).check()
    for error in errors:
        print(error)
    print(f"check_modules: {len(errors)} violation(s)" if errors else "check_modules: ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
