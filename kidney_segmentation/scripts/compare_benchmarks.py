#!/usr/bin/env python
"""Compare two sets of benchmark results, e.g. the shipped ones against a re-run.

    python scripts/compare_benchmarks.py results results/reproduced

For every ``benchmark_*`` directory present under both roots, prints the pooled point
estimates and object counts side by side and the largest absolute difference. Confidence
intervals are not compared: they come from a seeded bootstrap and match exactly whenever the
point estimates do.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

METRICS = ["PQ", "SQ", "DQ", "recall", "precision", "dice_per_gt", "hd95_um_median",
           "split_rate", "merge_rate"]
COUNTS = ["n_gt", "tp", "fp", "fn"]


def load(d: Path) -> dict:
    return json.loads((d / "benchmark.json").read_text())


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    ref_root, new_root = Path(argv[1]), Path(argv[2])
    names = sorted(d.name for d in ref_root.glob("benchmark_*")
                   if (d / "benchmark.json").exists() and (new_root / d.name / "benchmark.json").exists())
    if not names:
        print(f"no benchmark_* directories common to {ref_root} and {new_root}", file=sys.stderr)
        return 1

    worst = 0.0
    for name in names:
        a, b = load(ref_root / name), load(new_root / name)
        print(f"\n{name}")
        print(f"  {'':16s}{'shipped':>10s}{'re-run':>10s}{'diff':>10s}")
        for m in METRICS:
            x = a["pooled"].get(m, {}).get("estimate")
            y = b["pooled"].get(m, {}).get("estimate")
            if x is None or y is None:
                continue
            worst = max(worst, abs(y - x)) if m not in ("hd95_um_median",) else worst
            print(f"  {m:16s}{x:10.4f}{y:10.4f}{y - x:+10.4f}")
        for c in COUNTS:
            print(f"  {c:16s}{a['counts'].get(c, 0):10d}{b['counts'].get(c, 0):10d}"
                  f"{b['counts'].get(c, 0) - a['counts'].get(c, 0):+10d}")
    print(f"\nlargest absolute difference in a rate metric: {worst:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
