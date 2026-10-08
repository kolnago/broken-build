# ADK architecture guide v2.0 — §6 Core layer: domain models, ports, calculators, figures, derive, services, guardrails

Part of the guide split by section. Rule summary and file index: [../SKILL.md](../SKILL.md); overview, principles and layers: [overview.md](overview.md).

---

## 6. Core layer

### 6.1 Domain models

- **CORE-1** Domain models are Pydantic v2 with `frozen=True` and `extra="forbid"`.
- **CORE-2** Money, quantities, and rates are `Decimal`. Currency and unit are explicit fields.
- **CORE-3** Dates are explicit `as_of: date` parameters. No implicit "today" in core.
- **CORE-4** Keep three model families separate: **row models** (`data/`), **domain models** (`core/`), **tool/LLM schemas** (`tools/`, `workflows/`). One class never serves two families.

```python
# core/models/common.py
from datetime import date
from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, ConfigDict, StringConstraints

CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]

class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

class Money(DomainModel):
    amount: Decimal
    currency: CurrencyCode

class Position(DomainModel):
    position_id: str
    portfolio_id: str
    as_of: date
    market_value: Money

class Limit(DomainModel):
    portfolio_id: str
    as_of: date
    amount: Money
```

### 6.2 Ports

- **CORE-5** Repository interfaces are `typing.Protocol` classes in `core/ports.py`, named by intent, returning domain models.

```python
# core/ports.py
from datetime import date
from typing import Protocol
from app.core.models.common import Limit, Position

class PositionRepository(Protocol):
    def get_positions(self, portfolio_id: str, as_of: date) -> list[Position]: ...

class LimitRepository(Protocol):
    def get_limit(self, portfolio_id: str, as_of: date) -> Limit: ...
    def get_limit_history(self, portfolio_id: str, start: date, end: date) -> list[Limit]: ...
```

### 6.3 Calculators

- **CORE-6** Calculators are pure: no I/O, no clock, no randomness, no global state.
- **CORE-7** Rounding happens only at defined points via `core/calc/rounding.py` with an explicit mode.
- **CORE-8** Every calculator returns a result model that includes `Provenance`.
- **CORE-9** Each calculator has a `CALC_VERSION`; golden tests pin outputs.
- **CORE-10** Calculators produce the comparisons an analyst would make next (P3): flags, deltas, ratios, ranks. Do not stop at the raw value.

```python
# core/calc/utilization.py
from datetime import date
from decimal import Decimal
from app.core.calc.provenance import Provenance, fingerprint
from app.core.calc.rounding import quantize_ratio
from app.core.errors import CurrencyMismatch, InvalidLimit
from app.core.models.common import DomainModel, Limit, Money

CALC_NAME, CALC_VERSION = "limit_utilization", "1.1.0"

class UtilizationResult(DomainModel):
    exposure: Money
    limit: Money
    utilization: Decimal          # 0.8735
    headroom: Money
    breached: bool
    near_limit: bool              # utilization >= warn threshold (P3)
    provenance: Provenance

def limit_utilization(exposure: Money, limit: Limit, as_of: date, warn_at: Decimal = Decimal("0.9")) -> UtilizationResult:
    if exposure.currency != limit.amount.currency:
        raise CurrencyMismatch(exposure.currency, limit.amount.currency)
    if limit.amount.amount <= 0:
        raise InvalidLimit(limit.portfolio_id)
    util = quantize_ratio(exposure.amount / limit.amount.amount)
    return UtilizationResult(
        exposure=exposure, limit=limit.amount, utilization=util,
        headroom=Money(amount=limit.amount.amount - exposure.amount, currency=exposure.currency),
        breached=util > 1, near_limit=util >= warn_at,
        provenance=Provenance(calc_name=CALC_NAME, calc_version=CALC_VERSION, as_of=as_of,
                              inputs_fingerprint=fingerprint(exposure, limit, warn_at)),
    )
```

### 6.4 Figures

A `Figure` is the unit of exchange between code and the model. Tools return figures; the ledger records them; the verifier matches against them.

- **CORE-11** Every value the agent may see or repeat is a `Figure`: stable `figure_id`, exact `value`, `unit`, code-formatted `display`, `Provenance`.
- **CORE-12** Flags (`bool`) and categorical results (`str`) are figures too. "Breached", "trend: down", "rank 3 of 12" are computed, not inferred.

```python
# core/models/figures.py
from datetime import date
from decimal import Decimal
from app.core.calc.provenance import Provenance
from app.core.models.common import DomainModel

class Figure(DomainModel):
    figure_id: str                 # "limit.utilization"
    label: str                     # "Limit utilisation"
    value: Decimal | bool | str    # exact value; Decimal for numbers
    unit: str                      # "EUR", "ratio", "pct", "flag", "date", "count"
    display: str                   # "87.35 %"
    provenance: Provenance

class FigureSet(DomainModel):
    as_of: date
    figures: tuple[Figure, ...]
```

### 6.5 Derive operations

The `derive` tool (§8.4) lets the agent request a computation over figures it already has, without doing arithmetic itself. The operations are a closed, versioned set in core.

- **CORE-13** Derive operations live in `core/calc/derive.py`, take `Figure` inputs, return a `Figure`, enforce unit compatibility, and are unit-tested like any calculator.
- **CORE-14** The set is closed. Adding an operation is a code change with tests, not a prompt change.

```python
# core/calc/derive.py
from decimal import Decimal
from app.core.errors import UnitMismatch
from app.core.models.figures import Figure
from app.core.calc.rounding import quantize_ratio
from app.core.calc.formatting import fmt
from app.core.calc.provenance import Provenance, derived

OPERATIONS = ("difference", "ratio", "pct_change", "sum", "max", "min")

def difference(a: Figure, b: Figure) -> Figure:
    _same_unit(a, b)
    v = a.value - b.value
    return Figure(figure_id=f"derived.diff({a.figure_id},{b.figure_id})", label=f"{a.label} minus {b.label}",
                  value=v, unit=a.unit, display=fmt(v, a.unit), provenance=derived("difference", a, b))

def pct_change(new: Figure, old: Figure) -> Figure:
    _same_unit(new, old)
    if old.value == 0:
        raise ZeroDivisionError(old.figure_id)
    v = quantize_ratio((new.value - old.value) / abs(old.value))
    return Figure(figure_id=f"derived.pct_change({new.figure_id},{old.figure_id})", label=f"Change in {new.label}",
                  value=v, unit="ratio", display=fmt(v, "ratio"), provenance=derived("pct_change", new, old))

def _same_unit(a: Figure, b: Figure) -> None:
    if a.unit != b.unit or not isinstance(a.value, Decimal) or not isinstance(b.value, Decimal):
        raise UnitMismatch(a.figure_id, b.figure_id)
```

### 6.6 Services

- **CORE-15** A service orchestrates one use case: resolve inputs, fetch through ports, call calculators, return a `FigureSet`. No arithmetic, no framework types.
- **CORE-16** Services receive identity and entitlement scope explicitly and enforce them (`NotEntitled`).
- **CORE-17** Services are shaped around **analyst questions**, not tables: `limit_utilization`, `exposure_trend`, `top_contributors`, `collateral_coverage`. Coarse, question-shaped services make good tools.

### 6.7 Guardrails and errors

- **CORE-18** Number verification (§9) and strict-mode placeholder rendering (§9.5) live in `core/guardrails/`, pure and framework-free, tested with adversarial inputs.
- **CORE-19** Domain errors subclass `DomainError` with a safe `user_message`. Core never catches unexpected exceptions.
