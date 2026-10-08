# Module

An area of the domain, named as the business names it, holding bricks by kind. Not a brick: it
has no trust level and no test of its own; its bricks have those.

## Shape

```
modules/
├── __init__.py                 empty, or a docstring
├── exposure/                   what the bank is exposed to; knows nothing about breaches
│   ├── __init__.py             docstring; re-exports the public surface with __all__
│   ├── models/money/           bricks, one folder each
│   ├── ports/positions/
│   ├── calc/pdlc_exposure/
│   └── tools/exposure_tools/
├── investigation/              how any breach is investigated; knows nothing about one type
│   ├── __init__.py
│   ├── models/case/
│   ├── ports/ledger/
│   ├── callbacks/number_guard/
│   ├── skills/investigation_method/
│   └── fakes/scripted_model/
└── breaches/                   a group (M5): sibling modules, exports nothing
    ├── __init__.py             """Breach types, one module each."""
    ├── limit_overdraft/
    │   ├── __init__.py
    │   ├── models/limit_overdraft/
    │   ├── calc/overdraft/
    │   ├── tools/lo_tools/
    │   ├── skills/lo_method/
    │   └── agents/lo_investigator/
    └── collateral_shortfall/
```

```python
# modules/exposure/__init__.py
"""Exposure: positions, limits and market data of the bank, and the exposure calculated from
them as of a date. Used by every breach type; knows nothing about breaches."""

from .calc.pdlc_exposure import pdlc_exposure
from .models.money import Money
from .models.position import Position
from .ports.positions import PositionRepository, FakePositions
from .tools.exposure_tools import make_exposure_tools

__all__ = ["FakePositions", "Money", "Position", "PositionRepository", "make_exposure_tools",
           "pdlc_exposure"]
```

## The order

Declared once, top first. A module imports only modules below its own level; modules on one
level are independent. Groups are named with a trailing `.*`.

```toml
[tool.adk_modules]
order = [
  ["breaches.*"],
  ["investigation"],
  ["exposure"],
]
```

`scripts/check_modules.py` reads it, and so does the import-linter contract in
`python-rules/references/config.md`; the two check the same order in two ways, one on the
source tree and one on the installed package.

## Test

A module has no test of its own. `check_modules.py` checks that every brick in it has one
(B5), that its `__init__.py` exports what other modules import (M2), that it imports only
downward (M3) and that its kinds import inward (M4).

## Traps

- **Name the module after the domain concept, not after the data or the technology.**
  `exposure`, not `bigquery_positions`; `investigation`, not `common`. A name a risk manager
  would not use is a sign the cut is wrong.
- **Export the fake with the port.** Another module's tests need `FakePositions` as much as its
  code needs `PositionRepository`.
- **A module used by one other module is that module's part** (B8), nested inside it, not a
  sibling. It moves up when a second user appears.
- **Shared code with no domain name is not a module.** Put it in the brick that needs it, and
  wait for the second user (P4).
- **The group's `__init__.py` exports nothing.** `from modules.breaches import limit_overdraft`
  is a path import; apps and modules name the sibling in full: `modules.breaches.limit_overdraft`.
- **Add a new module to the order when it is created,** and say which level and why in the
  commit. A module missing from the order fails the check.

Not proven yet: this shape in a full project. The first one built on it is the proof.
