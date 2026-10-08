# Calculator brick

A pure function that produces numbers. Every piece of arithmetic in the repository lives in
one. Strict by construction.

## Shape

```
bricks/calc/order_total/
├── __init__.py            the functions, exported with __all__
└── test_order_total.py
```

```python
"""Calculator brick, strict. In: an Order or one of its lines. Out: the total as Money."""

def line_total(line: OrderLine) -> Money:
    return Money(amount=line.unit_price.amount * line.quantity, currency=line.unit_price.currency)

def order_total(order: Order) -> Money:
    currencies = {line.unit_price.currency for line in order.lines}
    if len(currencies) != 1:
        raise ValueError(f"order {order.order_id} needs lines in exactly one currency")
    amount = sum((line_total(line).amount for line in order.lines), Decimal(0))
    return Money(amount=amount, currency=currencies.pop())
```

## Test

Exact expected values written as `Decimal("1250.05")`, and the inputs that have no meaningful
answer (mixed currencies, an empty order) raising `ValueError`.

## Traps

- **No I/O, no clock, no model.** Everything a calculator needs is an argument.
- **Start a sum with `Decimal(0)`,** so the sum of nothing is still a `Decimal`.
- **When another brick needs a number, add a function here.** The order card needed a total
  per line, so `line_total` was added to the calculator instead of multiplying in the surface.
- **Refuse input that has no answer** instead of returning a guess.
- **Say the rounding in the docstring:** the precision and the mode, applied with
  `quantize`. If the request does not give them, ask; do not pick (P6). The same goes for
  what is being counted or averaged.
