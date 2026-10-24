"""ArcGIS fetch with pagination and caching (SPEC §5.1)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import requests

from .constants import ELEMENT_LAYER, INVENTORY_LAYER

log = logging.getLogger(__name__)


def _count(layer_url: str, where: str) -> int:
    params = {"where": where, "returnCountOnly": "true", "f": "json"}
    r = requests.get(layer_url + "/query", params=params, timeout=30)
    r.raise_for_status()
    return int(r.json()["count"])


def fetch_all(layer_url: str, where: str) -> List[dict]:
    """Page through an ArcGIS feature layer until the transfer limit is cleared."""
    rows: List[dict] = []
    offset = 0
    while True:
        params = {
            "where": where,
            "outFields": "*",
            "returnGeometry": "false",
            "orderByFields": "OBJECTID",
            "resultOffset": offset,
            "resultRecordCount": 1000,
            "f": "json",
        }
        r = requests.get(layer_url + "/query", params=params, timeout=30)
        r.raise_for_status()
        j = r.json()
        if "error" in j:
            raise RuntimeError(j["error"])
        batch = [f["attributes"] for f in j.get("features", [])]
        rows += batch
        offset += len(batch)
        if not batch or not j.get("exceededTransferLimit"):
            break
    return rows


def fetch_with_count_check(layer_url: str, where: str) -> List[dict]:
    expected = _count(layer_url, where)
    rows = fetch_all(layer_url, where)
    if len(rows) != expected:
        raise RuntimeError(
            f"Row count mismatch for {layer_url}: fetched {len(rows)}, server says {expected}"
        )
    return rows


def fetch_or_cache(layer_url: str, where: str, cache_path: Path) -> List[dict]:
    """Fetch live and write the cache; on network failure fall back to cache."""
    try:
        rows = fetch_with_count_check(layer_url, where)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(rows))
        return rows
    except (requests.RequestException, RuntimeError) as exc:
        if cache_path.exists():
            log.warning("Fetch failed (%s); using cached %s", exc, cache_path)
            return json.loads(cache_path.read_text())
        raise


def fetch_inventory(cache_path: Path, state_fips: str = "25") -> List[dict]:
    return fetch_or_cache(INVENTORY_LAYER, f"state_code_i3='{state_fips}'", cache_path)


def fetch_elements(cache_path: Path, state_fips: str = "25") -> List[dict]:
    return fetch_or_cache(ELEMENT_LAYER, f"state='{state_fips}'", cache_path)
