# Model brick

A typed value that bricks pass to each other. Strict by construction.

## Shape

```
bricks/models/money/
├── __init__.py     the class, exported with __all__
└── test_money.py
```

```python
"""Model brick, strict. An exact amount of money: a Decimal amount and an ISO currency code."""

class Money(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    amount: Decimal
    currency: Currency          # Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]

    @field_validator("amount", mode="before")
    @classmethod
    def _no_float(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("money is never a float; pass a Decimal or a string")
        return value
```

## Test

Accepts a `Decimal` and a string, rejects a `float`, rejects a malformed currency.

## Traps

- **Pydantic turns a `float` into a `Decimal` silently.** `Money(amount=10.5)` is accepted
  unless a `mode="before"` validator refuses it (B2).
- **Raise `ValueError` in the validator, not `TypeError`.** Pydantic reports a `ValueError` as
  a `ValidationError`; a `TypeError` escapes as it is.
- **Keep models free of behaviour that computes.** Arithmetic belongs in a
  [calculator](calculator.md).
