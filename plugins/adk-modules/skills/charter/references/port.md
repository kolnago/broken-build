# Port, adapter and fake

One brick: the `Protocol` that other bricks depend on, the code that implements it against a
real system, and the in-memory stand-in for tests. Strict by construction.

## Shape

```
modules/orders/ports/orders/
├── __init__.py          docstring; re-exports everything below with __all__
├── port.py              the domain types, the error, the Protocol
├── json_file.py         the adapter for a real source
├── fake.py              the in-memory stand-in
├── sample_orders.json   sample data for entry points
└── test_orders.py
```

```python
# port.py
class OrderNotFound(LookupError): ...

class OrderRepository(Protocol):
    def get(self, order_id: str) -> Order: ...
```

`__init__.py` also exports `SAMPLE_ORDERS`, the path of the sample data, so an entry point
can run the brick's users without inventing data.

## Test

One test runs the same assertions against the adapter and the fake, so the fake cannot drift
from the real behaviour:

```python
for repository in [FakeOrders([order]), JsonFileOrders(path)]:
    assert repository.get("A-1").lines[0].quantity == 2
    with pytest.raises(OrderNotFound):
        repository.get("missing")
```

## Traps

- **The port takes and returns domain models,** never rows, dicts or driver types.
- **A missing record is the port's own error type,** raised by adapter and fake alike. The
  caller decides what to tell the user.
- **Users depend on the `Protocol` only** (B4). Which adapter is used is chosen in an entry
  point (B7).
- **Adding a method to a port is an ordinary change.** Add it to the `Protocol`, the adapter
  and the fake together, and to the shared test.
- **Amounts in stored data are strings** (`"500.00"`), so no `float` appears on the way in.
- **Export the `Protocol`, the error and the fake from the module** (M2). Another module's
  tests need the fake; the adapter stays inside, chosen by entry points.
