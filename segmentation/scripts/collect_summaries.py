#!/usr/bin/env python
"""Collect the per-slide summary.json files of a batch run into one CSV.

    python scripts/collect_summaries.py results/my_batch

Looks for ``<dir>/*/summary.json`` (one ``wsi_infer.py`` output directory per slide, as
written by ``scripts/batch_infer.sh``) and writes ``<dir>/summary.csv`` with one row per
slide: tissue area, instance counts, total area and density per mm^2 of tissue for every
class. Densities are the comparable quantity across sections; raw counts are not, because
sections differ in tissue area.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    out_dir = Path(argv[1]).resolve()
    summaries = sorted(out_dir.glob("*/summary.json"))
    if not summaries:
        print(f"no */summary.json found under {out_dir}", file=sys.stderr)
        return 1

    loaded = [(sf.parent.name, json.loads(sf.read_text())) for sf in summaries]
    classes = sorted({c for _, s in loaded for c in s.get("counts_by_class", {})})

    rows = []
    for name, s in loaded:
        counts = s.get("counts_by_class", {})
        areas = s.get("area_mm2_by_class", {})
        dens = s.get("density_per_mm2_tissue", {})
        row = {
            "run": name,
            "slide": Path(s["slide"]).name,
            "checkpoint": Path(str(s.get("checkpoint", ""))).name,
            "width": s["slide_size_work"][0],
            "height": s["slide_size_work"][1],
            "working_mpp": s["working_mpp"],
            "tissue_fraction": round(s["tissue_fraction"], 6),
            "tissue_area_mm2": round(s["tissue_area_mm2"], 4),
            "n_instances": s["n_instances"],
            "glass_instance_rate": s.get("glass", {}).get("glass_instance_rate"),
            "infer_minutes": round(s.get("infer_minutes", float("nan")), 2),
        }
        for c in classes:
            row[f"n_{c}"] = counts.get(c, 0)
            row[f"mm2_{c}"] = round(areas.get(c, 0.0), 5)
            row[f"per_mm2_{c}"] = round(dens.get(c, 0.0), 3)
        rows.append(row)

    dest = out_dir / "summary.csv"
    with open(dest, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} slides -> {dest}")
    print(f"total instances: {sum(r['n_instances'] for r in rows):,}")
    bad = [r["run"] for r in rows if (r["glass_instance_rate"] or 0) > 0.01]
    print(f"slides with glass instance rate > 1%: {bad if bad else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
