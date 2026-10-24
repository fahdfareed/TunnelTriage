"""Element dictionary, fallback-first (SPEC §5.2).

Names are not in the feed. We build a complete fallback for every element number
present in the data, then (optionally, timeboxed) enrich with SNTI PDF names.
The fallback alone is sufficient for all analytics; names never block scoring.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Dict, List

from .config import Config

log = logging.getLogger(__name__)

# SNTI categories with default criticality (SPEC §5.2).
CATEGORY_CRITICALITY_DEFAULT = {
    "Structural": 4,
    "Civil": 2,
    "Joints & Gaskets": 3,
    "Mechanical": 4,
    "Electrical": 4,
    "Fire/Life Safety/Security": 5,
    "Signs": 2,
    "Protective Systems": 2,
    "Unknown": 3,
}


def _max_quantity_by_element(elements: List[dict]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for row in elements:
        n = int(row["element_number"])
        q = int(row.get("total_quantity") or 0)
        out[n] = max(out.get(n, 0), q)
    return out


def build_fallback(elements: List[dict], cfg: Config) -> Dict[int, dict]:
    """A complete dictionary row for every element number in the data (SPEC §5.2 step 2)."""
    max_q = _max_quantity_by_element(elements)
    rows: Dict[int, dict] = {}
    for n, qmax in max_q.items():
        unit = "each" if qmax <= 50 else "area/length"
        is_system = unit == "each"
        rows[n] = {
            "element_number": n,
            "name": f"Element {n}",
            "category": "Unknown",
            "unit": unit,
            "criticality": 3,
            "is_system_element": is_system,
            "source": "fallback",
        }
    return rows


def _apply_criticality(rows: Dict[int, dict], cfg: Config) -> None:
    """Category defaults, overhead-keyword rule, then explicit overrides (SPEC §5.2)."""
    crit_by_cat = cfg.criticality_by_category
    for n, row in rows.items():
        row["criticality"] = crit_by_cat.get(row["category"], 3)
        name_lc = row["name"].lower()
        if any(kw in name_lc for kw in cfg.overhead_keywords):
            row["criticality"] = 5
        if n in cfg.criticality_overrides:
            row["criticality"] = cfg.criticality_overrides[n]


def snti_category(n: int) -> str:
    """SNTI element-number ranges -> category (SPEC §3.3)."""
    for upper, cat in (
        (10130, "Structural"), (10150, "Joints & Gaskets"), (10200, "Civil"),
        (10400, "Mechanical"), (10650, "Electrical"), (10850, "Fire/Life Safety/Security"),
        (10950, "Signs"),
    ):
        if n < upper:
            return cat
    return "Protective Systems"


def try_snti_enrich(rows: Dict[int, dict], pdf_path: Path | None) -> bool:
    """Attempt SNTI PDF name extraction. Returns True if it enriched >= 30 elements.

    Timeboxed/opportunistic: if pdfplumber or the PDF is unavailable, we silently
    keep the fallback. Analytics do not depend on this.
    """
    if not pdf_path or not pdf_path.exists():
        return False
    try:
        import re

        import pdfplumber  # type: ignore

        text_parts: List[str] = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                text_parts.append(t)
        text = "\n".join(text_parts)
        # SNTI element table lines look like "10130 Strip Seal Expansion Joint length, ft"
        # (a category word from the left column may precede the number).
        pat = re.compile(r"\b(1\d{4})\s+([A-Za-z][A-Za-z/ \-]+?)\s+(area, ft2|length, ft|each)\s*$", re.M)
        unit_map = {"area, ft2": "area/length", "length, ft": "area/length", "each": "each"}
        enriched = 0
        for m in pat.finditer(text):
            n = int(m.group(1))
            if n not in rows:
                continue
            name = m.group(2).strip()
            unit_raw = (m.group(3) or "").strip().lower()
            rows[n]["name"] = name
            rows[n]["category"] = snti_category(n)
            rows[n]["source"] = "SNTI"
            if unit_raw in unit_map:
                rows[n]["unit"] = unit_map[unit_raw]
                rows[n]["is_system_element"] = unit_map[unit_raw] == "each"
            enriched += 1
        if enriched >= 30:
            log.info("SNTI enrichment applied to %d elements", enriched)
            return True
        log.info("SNTI enrichment yielded only %d elements; keeping fallback", enriched)
        return False
    except Exception as exc:  # pragma: no cover - opportunistic
        log.warning("SNTI enrichment failed (%s); keeping fallback", exc)
        return False


def build_dictionary(elements: List[dict], cfg: Config, pdf_path: Path | None = None) -> Dict[int, dict]:
    rows = build_fallback(elements, cfg)
    try_snti_enrich(rows, pdf_path)
    _apply_criticality(rows, cfg)
    return rows


def write_csv(rows: Dict[int, dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["element_number", "name", "category", "unit", "criticality",
              "is_system_element", "source"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for n in sorted(rows):
            w.writerow(rows[n])


def read_csv(path: Path) -> Dict[int, dict]:
    rows: Dict[int, dict] = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            n = int(r["element_number"])
            rows[n] = {
                "element_number": n,
                "name": r["name"],
                "category": r["category"],
                "unit": r["unit"],
                "criticality": int(r["criticality"]),
                "is_system_element": r["is_system_element"] in ("True", "true", "1"),
                "source": r["source"],
            }
    return rows
