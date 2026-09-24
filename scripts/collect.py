#!/usr/bin/env python3
"""CLI entry point: fetches data.go.kr sources and writes static JSON
snapshots for the kr-baby-now map app.

Usage:
    python3 scripts/collect.py                 # run every layer group
    python3 scripts/collect.py peds obgyn       # run only these layer groups
    python3 scripts/collect.py --list           # list available layer names

Each layer group writes its own file(s) under data/layers/ or data/lists/
and merges its summary into data/meta.json. Layer groups run in a fixed
canonical order (not argv order) because busan-postnatal's overlap-merge
step depends on postnatal.json already existing on disk.
"""
from __future__ import annotations

import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.keyutil import redact  # noqa: E402
from lib.schema import update_meta  # noqa: E402
from layers import peds_obgyn, postnatal, playground, idolbom, vaccine, busan  # noqa: E402

# Canonical execution order. postnatal MUST run before busan so that
# busan-postnatal's overlap check can read the freshly written
# data/layers/postnatal.json.
LAYER_GROUPS = {
    "postnatal": [("postnatal", postnatal.collect_postnatal)],
    "peds": [("peds", peds_obgyn.collect_peds)],
    "obgyn": [("obgyn", peds_obgyn.collect_obgyn)],
    "idolbom": [
        ("idolbom", idolbom.collect_idolbom),
        ("idolbom-fee", idolbom.collect_idolbom_fee),
        ("idolbom-docs", idolbom.collect_idolbom_docs),
    ],
    "vaccine": [("vaccine", vaccine.collect_vaccine)],
    "playground": [("playground", playground.collect_playground)],
    "busan": [
        ("busan-daycare", busan.collect_busan_daycare),
        ("busan-nursing", busan.collect_busan_nursing),
        ("busan-kidscafe", busan.collect_busan_kidscafe),
        ("busan-postnatal", busan.collect_busan_postnatal),
        ("busan-birth-grant", busan.collect_busan_birth_grant),
    ],
}

CANONICAL_ORDER = ["postnatal", "peds", "obgyn", "idolbom", "vaccine", "playground", "busan"]


def main(argv):
    if "--list" in argv:
        for name in CANONICAL_ORDER:
            print(name)
        return 0

    requested = [a for a in argv if not a.startswith("-")]
    if requested:
        unknown = [r for r in requested if r not in LAYER_GROUPS]
        if unknown:
            print(f"Unknown layer group(s): {unknown}. Available: {CANONICAL_ORDER}", file=sys.stderr)
            return 2
        groups_to_run = [g for g in CANONICAL_ORDER if g in requested]
    else:
        groups_to_run = CANONICAL_ORDER

    print(f"Running layer groups: {groups_to_run}")

    overall_ok = True
    for group in groups_to_run:
        for sub_name, fn in LAYER_GROUPS[group]:
            t0 = time.time()
            print(f"--- [{group}/{sub_name}] starting ---")
            try:
                meta_entries, detail = fn()
            except Exception as e:  # noqa: BLE001
                overall_ok = False
                print(f"!!! [{group}/{sub_name}] FAILED: {redact(str(e))}")
                traceback.print_exc()
                continue
            update_meta(meta_entries)
            dt = time.time() - t0
            for k, v in meta_entries.items():
                print(
                    f"--- [{group}/{sub_name}] done in {dt:.1f}s: "
                    f"{k} count={v['count']} dropped_no_coord={v['dropped_no_coord']}"
                )
            for k, v in detail.items():
                print(f"    detail[{k}] = {v}")

    print("=== COLLECT DONE ===" if overall_ok else "=== COLLECT FINISHED WITH ERRORS ===")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
