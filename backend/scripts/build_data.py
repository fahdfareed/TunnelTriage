"""Fetch -> dictionary -> process. Idempotent. Run from backend/ (SPEC §5)."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATA_DIR, get_config  # noqa: E402
from app.dictionary import build_dictionary, write_csv  # noqa: E402
from app.fetch import fetch_elements, fetch_inventory  # noqa: E402
from app.process import (  # noqa: E402
    build_data_notes,
    build_groups,
    normalize_elements,
    normalize_tunnels,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_data")

RAW = DATA_DIR / "raw"
PROCESSED = DATA_DIR / "processed"


def main() -> None:
    cfg = get_config()
    fips = cfg.state_fips

    log.info("Fetching inventory (state_code_i3=%s)...", fips)
    inventory = fetch_inventory(RAW / "inventory_ma.json", fips)
    log.info("  %d tunnels", len(inventory))

    log.info("Fetching elements (state=%s)...", fips)
    elements = fetch_elements(RAW / "elements_ma.json", fips)
    log.info("  %d element rows", len(elements))

    assert len(inventory) >= 40, f"expected >= 40 tunnels, got {len(inventory)}"

    log.info("Building element dictionary (fallback-first)...")
    snti_pdf = DATA_DIR / "hif15006.pdf"  # optional; fallback used if absent
    dictionary = build_dictionary(elements, cfg, snti_pdf if snti_pdf.exists() else None)
    write_csv(dictionary, DATA_DIR / "element_dictionary.csv")
    sources = {d["source"] for d in dictionary.values()}
    log.info("  dictionary covers %d elements (source: %s)", len(dictionary), ", ".join(sorted(sources)))

    log.info("Normalizing...")
    tunnels = normalize_tunnels(inventory)
    element_rows = normalize_elements(elements, cfg)
    groups = build_groups(tunnels)
    notes = build_data_notes(element_rows, tunnels, cfg)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "tunnels.json").write_text(json.dumps(tunnels, indent=2))
    (PROCESSED / "elements.json").write_text(json.dumps(element_rows, indent=2))
    (PROCESSED / "data_notes.json").write_text(json.dumps(notes, indent=2))

    log.info("  %d map groups", len(groups))
    log.info("  suspect elements excluded: %s", notes["suspect_elements"]["numbers"])
    log.info("Done. Processed files written to %s", PROCESSED)


if __name__ == "__main__":
    main()
