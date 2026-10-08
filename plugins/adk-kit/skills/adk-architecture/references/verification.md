# ADK architecture guide v2.0 — §9 Number verification

Part of the guide split by section. Rule summary and file index: [../SKILL.md](../SKILL.md); overview, principles and layers: [overview.md](overview.md).

---

## 9. Number verification

This is the mechanism that makes P1 true regardless of how the agent behaves.

### 9.1 What is checked

- **VER-1** Every numeric token in the final answer must be **grounded**: it matches a ledger figure (§9.2) or appears verbatim in the user's message for this turn.
- **VER-2** Tokens containing digits that are not numbers (dates, IDs, codes) must appear verbatim in a ledger figure's `display` or `value`, or in the user's message.
- **VER-3** Ungrounded tokens produce violations. The shell retries once with the violation list, then falls back (`SH-3`).
- **VER-4** Violation counts are a metric. A rising rate signals prompt drift or a model regression.

### 9.2 Matching rules

A stated number `n` with `d` decimal places matches ledger value `v` if any of these hold:

1. `n` equals `v` exactly.
2. `n` equals `v` quantized to `d` decimals (the model rounded: "87.4 %" for 0.8735 in `pct` display).
3. `n` equals `v` after the unit's display scaling (`ratio` 0.8735 stated as 87.35 or 87.4 when the display unit is percent).

Scale words ("1.25 million") are **not** matched by default; the display already chooses a scale. Extending the matcher is an ADR (OD-2).

### 9.3 Reference implementation

```python
# core/guardrails/numbers.py
import re
from decimal import Decimal, ROUND_HALF_EVEN
from app.core.models.common import DomainModel
from app.core.models.figures import Figure

NUMBER = re.compile(r"(?<![\w.])[-+]?\d{1,3}(?:[ ,]\d{3})+(?:\.\d+)?|(?<![\w.])[-+]?\d+(?:\.\d+)?(?![\w.])")
DIGIT_TOKEN = re.compile(r"\S*\d\S*")
SCALES = {"ratio": (Decimal(100),), "pct": (Decimal(1),)}      # ratio may be stated as percent

class VerificationReport(DomainModel):
    ok: bool
    violations: tuple[str, ...]

def _normalize(s: str) -> Decimal:
    return Decimal(s.replace(",", "").replace(" ", ""))

def _matches(n: Decimal, v: Decimal, unit: str) -> bool:
    d = -n.as_tuple().exponent if n.as_tuple().exponent < 0 else 0
    q = Decimal(1).scaleb(-d)
    for scale in (Decimal(1), *SCALES.get(unit, ())):
        sv = v * scale
        if n == sv or n == sv.quantize(q, rounding=ROUND_HALF_EVEN):
            return True
    return False

def verify_numbers(answer: str, ledger: dict[str, Figure], user_text: str) -> VerificationReport:
    numeric = [(f.value, f.unit) for f in ledger.values() if isinstance(f.value, Decimal)]
    verbatim = {t for f in ledger.values() for t in DIGIT_TOKEN.findall(f"{f.display} {f.value}")}
    verbatim |= set(DIGIT_TOKEN.findall(user_text))
    violations: list[str] = []
    for raw in DIGIT_TOKEN.findall(answer):
        tok = raw.strip(".,;:)(\"'")
        if raw in verbatim or tok in verbatim:
            continue
        nums = NUMBER.findall(tok)
        if not nums:
            violations.append(f"ungrounded token {tok!r}")
            continue
        for num in nums:
            n = _normalize(num)
            if not any(_matches(n, v, u) for v, u in numeric):
                violations.append(f"ungrounded number {num!r}")
    return VerificationReport(ok=not violations, violations=tuple(violations))
```

Tested behaviour (see `tests/unit/guardrails/test_numbers.py`): exact and rounded restatements pass; ratio-as-percent passes; a sum the model computed itself fails; a date from the user's message passes; an invented ID fails.

### 9.4 Known limits

Verification catches **invented and computed numbers**. It cannot catch **wrong qualitative claims** ("well within limits" when `near_limit` is true, "roughly doubled" when the change is 60 %). Two mitigations:

- Precomputed flags (`CORE-10`) reduce the model's need to judge magnitudes.
- **Consistency evals** (`TEST-3`): adversarial cases where the flags and the tempting narrative disagree; the eval asserts the answer agrees with the flags.

### 9.5 Strict mode for Pattern B

Fixed workflows for regulated output keep the 0.1 mechanism: the narration agent has an output schema with **no numeric fields**, refers to figures only as `{{figure_id}}`, a `check_grounding` node rejects any digit outside a placeholder, and code renders the final text by substituting `display`. It is stricter and less natural; use it where the process demands it.
