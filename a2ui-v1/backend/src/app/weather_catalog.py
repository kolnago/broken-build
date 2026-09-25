"""The demo catalog: A2UI v0.9 basic catalog + the custom components in catalog/.

`catalog/weather_catalog.json` is the single source of truth for custom components. It only
declares its own components; this provider merges them into the bundled basic catalog so
the result is a self-contained catalog (basic components `$ref` the catalog's own `$defs`).
The frontend does the same merge with `basicCatalog` (frontend/src/catalog.ts).
"""

import copy
import json
from typing import Any

from a2ui.basic_catalog.provider import BundledCatalogProvider
from a2ui.schema.catalog import CatalogConfig
from a2ui.schema.catalog_provider import A2uiCatalogProvider

from app.a2ui_support import A2UI_VERSION
from app.paths import CATALOG_DIR

CATALOG_FILE = CATALOG_DIR / "weather_catalog.json"


class MergedCatalogProvider(A2uiCatalogProvider):
    def load(self) -> dict[str, Any]:
        custom = json.loads(CATALOG_FILE.read_text())
        merged = copy.deepcopy(BundledCatalogProvider(A2UI_VERSION).load())
        merged["catalogId"] = custom["catalogId"]
        merged["$id"] = custom["catalogId"]
        merged["components"].update(custom["components"])
        merged["$defs"]["anyComponent"]["oneOf"] += [
            {"$ref": f"#/components/{name}"} for name in custom["components"]
        ]
        return merged


def weather_catalog_config() -> CatalogConfig:
    return CatalogConfig(name="weather", provider=MergedCatalogProvider())
