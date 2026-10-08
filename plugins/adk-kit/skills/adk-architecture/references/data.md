# ADK architecture guide v2.0 — §7 Data layer: repositories and SQL

Part of the guide split by section. Rule summary and file index: [../SKILL.md](../SKILL.md); overview, principles and layers: [overview.md](overview.md).

---

## 7. Data layer

- **DATA-1** Repositories implement `core.ports` and return domain models via row models.
- **DATA-2** SQL lives in `data/sql/<area>/<query>.sql`, one query per file, loaded with `importlib.resources`.
- **DATA-3** Values are passed only as named query parameters. Identifiers that cannot be parameters (project, dataset) come from validated settings only.
- **DATA-4** Every query feeding reported figures filters on an explicit `as_of`.
- **DATA-5** Every job sets `maximum_bytes_billed`, a timeout, and a row cap. The service account is read-only on curated datasets or views.
- **DATA-6** **Repositories retrieve; calculators compute.** SQL that aggregates for performance is *certified SQL*: named, versioned, reviewed like a calculator, golden-tested.
- **DATA-7** Money columns are `NUMERIC`/`BIGNUMERIC` → `Decimal`. A `FLOAT64` money column is a data-quality issue to raise, not convert silently.
- **DATA-8** Repositories are synchronous; async callers offload with `asyncio.to_thread`.
- **DATA-9** Every port has an in-memory fake in `tests/fakes/`.

```sql
-- data/sql/positions/get_positions.sql   (retrieval only — DATA-6)
SELECT position_id, portfolio_id, as_of_date AS as_of, market_value, currency
FROM `{{dataset}}.positions`
WHERE portfolio_id = @portfolio_id AND as_of_date = @as_of
```

```python
# data/repositories/positions_bq.py
from datetime import date
from importlib.resources import files
from google.cloud import bigquery
from app.config import DataSettings
from app.core.models.common import Position
from app.data.rows import PositionRow

_SQL = (files("app.data") / "sql" / "positions" / "get_positions.sql").read_text()

class BigQueryPositionRepository:
    def __init__(self, client: bigquery.Client, settings: DataSettings) -> None:
        self._client, self._settings = client, settings
        self._sql = _SQL.replace("{{dataset}}", settings.dataset)   # validated identifier (DATA-3)

    def get_positions(self, portfolio_id: str, as_of: date) -> list[Position]:
        cfg = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("portfolio_id", "STRING", portfolio_id),
                              bigquery.ScalarQueryParameter("as_of", "DATE", as_of)],
            maximum_bytes_billed=self._settings.max_bytes_billed)
        rows = self._client.query(self._sql, job_config=cfg).result(
            timeout=self._settings.query_timeout_s, max_results=self._settings.max_rows)
        return [PositionRow.model_validate(dict(r)).to_domain() for r in rows]
```
