#!/usr/bin/env python
"""Figures for a benchmark_segmentation.py run: failure examples and result charts.

    python scripts/plot_benchmark.py --bench-dir results/benchmark_mouse_val

Reads ``benchmark.json``, ``objects.csv`` and ``tiles.csv`` from --bench-dir and writes PNGs
to ``<bench-dir>/figures/``. The example panels re-open the slides and predictions named in
the run's provenance, so they show the pixels the numbers were computed on.

    examples_<type>.png   image crops per failure type: annotation (cyan, solid) against
                          prediction (yellow, dashed), a white cross on the object in question
    metrics.png           pooled and per-slide metrics with confidence intervals
    by_class.png          the same per ground-truth class (and by_source.png where present)
    failure_types.png     how many annotated objects fail, and how
    dice_vs_hd95.png      why both are reported: objects with high Dice and a large HD95
    distributions.png     per-object Dice and HD95
    size_quartiles.png    metrics by annotated object size
    tile_map.png          where on each slide the low-scoring tiles are
    stain_drift.png       metrics under controlled stain scaling (only if the run has it)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

import _bootstrap  # noqa: F401
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

# Categorical slots 1-3 validate for all-pairs colour-vision separation; nothing here uses
# more than three hues plus neutral grey. Text is always ink, never a series colour.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GREY, INK, INK2, GRID, SURFACE = "#8c8b86", "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#dbe9fa", "#2a78d6", "#0f3b73"])
GT_COLOR, PRED_COLOR = "#00e5ff", "#ffd400"

FAILURES = {
    "merge": "Merge — one prediction covers ≥ 20% of two or more annotated objects",
    "split": "Split — two or more predictions each cover ≥ 20% of one annotated object",
    "miss": "Miss — annotated object with no prediction overlapping it (best IoU < 0.10)",
    "poor_overlap": "Poor overlap — a prediction is there, but IoU ≤ 0.5",
    "leak": "Leak — matched, but > 5% of the prediction lies beyond 5 px of the annotation",
    "high_hd95": "Largest HD95 among matched objects that are neither merged nor split",
    "fp_on_object": "False positive on an annotated object (a fragment or duplicate)",
    "fp_on_background": "False positive on trusted background",
}
LABELS = {"PQ": "PQ", "recall": "Recall", "precision": "Precision",
          "dice_per_gt": "Dice per annotated object\n(missed = 0)",
          "dice_matched": "Dice, matched only", "hd95_um_mean": "HD95 mean (µm)",
          "hd95_um_median": "HD95 median (µm)", "merge_rate": "Merge rate",
          "split_rate": "Split rate", "fg_dice_px": "Foreground Dice (pixels)"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "text.color": INK, "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150,
})


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def load_objects(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            for k in ("cx", "cy", "gt_area", "pred_area", "iou", "dice", "best_iou", "hd95_um",
                      "hd95_px", "h95_gt_to_pred_px", "h95_pred_to_gt_px", "leak_frac",
                      "area_ratio"):
                r[k] = _float(r[k])
            rows.append(r)
    return rows


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def save(fig, path):
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


# ------------------------------------------------------------------- examples
def pick_examples(objs, kind, n):
    """Choose which objects to show. Ranked types show the worst; the others an even spread
    across object size, so the panel is representative rather than the extreme tail."""
    if kind == "leak":
        pool = sorted([o for o in objs if o["failure"] == "leak"], key=lambda o: -o["leak_frac"])
    elif kind == "high_hd95":
        pool = sorted([o for o in objs if o["status"] == "TP" and o["failure"] in ("ok", "leak")
                       and math.isfinite(o["hd95_um"])], key=lambda o: -o["hd95_um"])
    else:
        pool = sorted([o for o in objs if o["failure"] == kind],
                      key=lambda o: o["pred_area"] if o["status"] == "FP" else o["gt_area"])
        if len(pool) > n:
            pool = [pool[i] for i in np.linspace(0, len(pool) - 1, 3 * n).round().astype(int)]
    out = []
    for o in pool:      # a merge yields one record per fused object: show each site once
        if all(o["slide"] != p["slide"] or math.hypot(o["cx"] - p["cx"], o["cy"] - p["cy"]) > 150
               for p in out):
            out.append(o)
        if len(out) == n:
            break
    return out


class SlideSource:
    """Image, annotation and prediction access for the slides of one benchmark run."""

    def __init__(self, res):
        import benchmark_segmentation as bench
        from kidney_panoptic.data.manifest import load_manifest
        from kidney_panoptic.eval.ground_truth import load_slide_annotations

        prov = res["provenance"]
        rows = {r["slide_id"]: r for r in load_manifest(prov["manifest"],
                                                        splits=(prov["split"],))}
        self.slides = {}
        for sid, info in prov["slides"].items():
            pred = bench.load_prediction(Path(info["prediction_dir"]), [])
            reader = bench.open_reader(rows[sid], pred)
            to_work = 1.0 if pred["cfg"]["patch"].get("annotations_space", "full") == "level" \
                else reader.scale_full_to_work
            ann = load_slide_annotations(rows[sid]["geojson_path"], pred["spec"], to_work)
            self.slides[sid] = (pred, reader, ann)

    def crop(self, sid, cx, cy, half):
        from kidney_panoptic.eval.ground_truth import rasterize_rect

        pred, reader, ann = self.slides[sid]
        W, H = reader.level_dimensions_work
        x0, y0 = int(max(0, cx - half)), int(max(0, cy - half))
        x1, y1 = int(min(W, cx + half)), int(min(H, cy + half))
        rgb = reader.read_region_work(x0, y0, x1 - x0, y1 - y0)
        gt, _, _ = rasterize_rect(ann, pred["spec"], (x0, y0, x1, y1))
        px, py = pred["region"][:2]
        pm = pred["map"][y0 - py:y1 - py, x0 - px:x1 - px]
        return rgb, gt, pm, (x0, y0), pred["mpp"]


def _outlines(ax, lbl, color, style, width):
    for i in np.unique(lbl):
        if i:
            ax.contour(lbl == i, levels=[0.5], colors=[color], linewidths=width,
                       linestyles=style)


def plot_examples(objs, source, kind, out, n=8, cols=4):
    picks = pick_examples(objs, kind, n)
    if not picks:
        return
    rows = math.ceil(len(picks) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(3.3 * cols, 3.55 * rows + 0.75),
                             squeeze=False)
    total = sum(o["failure"] == kind for o in objs) if kind != "high_hd95" else None
    for ax in axes.ravel():
        ax.axis("off")
    for ax, o in zip(axes.ravel(), picks):
        area = max(a for a in (o["gt_area"], o["pred_area"]) if math.isfinite(a))
        half = int(np.clip(2.2 * math.sqrt(area), 170, 520))
        rgb, gt, pm, (x0, y0), mpp = source.crop(o["slide"], o["cx"], o["cy"], half)
        ax.imshow(rgb)
        _outlines(ax, gt, GT_COLOR, "solid", 1.5)
        _outlines(ax, pm, PRED_COLOR, "dashed", 1.3)
        ax.plot(o["cx"] - x0, o["cy"] - y0, marker="+", color="white", markersize=11,
                markeredgewidth=2.2)
        ax.plot(o["cx"] - x0, o["cy"] - y0, marker="+", color=INK, markersize=9,
                markeredgewidth=0.9)
        bar = 50 / mpp                                   # 50 µm scale bar
        h = rgb.shape[0]
        ax.plot([8, 8 + bar], [h - 10, h - 10], color="white", linewidth=3,
                solid_capstyle="butt")
        ax.text(8, h - 16, "50 µm", color="white", fontsize=7, va="bottom")
        cls = o["gt_class"] or o["pred_class"]
        if o["status"] == "TP":
            stat = f"Dice {o['dice']:.2f} · HD95 {o['hd95_um']:.1f} µm"
            if kind == "leak":
                stat += f" · leak {o['leak_frac']:.0%}"
        elif o["status"] == "FN":
            stat = f"unmatched · best IoU {o['best_iou']:.2f}"
        else:
            stat = f"unmatched prediction · {o['pred_area']:.0f} px"
        ax.set_title(f"{cls.replace('tubule_', '')} — {stat}\n{o['slide']} "
                     f"({o['cx']:.0f}, {o['cy']:.0f})", fontsize=7.5, fontweight="normal",
                     color=INK, loc="left")
    count = f"  ({total} in this run; {len(picks)} shown)" if total is not None else ""
    fig.suptitle(FAILURES[kind] + count, x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.legend(handles=[Line2D([], [], color=GT_COLOR, lw=2, label="annotation"),
                        Line2D([], [], color=PRED_COLOR, lw=2, ls="--", label="prediction"),
                        Line2D([], [], color=INK, marker="+", ls="", markersize=9,
                               label="object in question")],
               loc="upper right", ncol=3, frameon=False, fontsize=8, facecolor=SURFACE,
               bbox_to_anchor=(0.995, 0.965 if rows > 1 else 0.94))
    fig.tight_layout(rect=(0, 0, 1, 0.94 if rows > 1 else 0.90), h_pad=2.2)
    fig.subplots_adjust(hspace=0.16)
    save(fig, out / f"examples_{kind}.png")


# --------------------------------------------------------------------- charts
def _forest(ax, names, metrics, key, color=BLUE):
    """Point estimate and interval per row; value printed beside each."""
    ys = np.arange(len(names))[::-1]
    for y, m in zip(ys, metrics):
        est = (m or {}).get(key, {}).get("estimate")
        if est is None:
            ax.text(0.02, y, "n/a", transform=ax.get_yaxis_transform(), va="center",
                    color=INK2, fontsize=8)
            continue
        lo, hi = m[key].get("ci_low"), m[key].get("ci_high")
        if lo is not None:
            ax.plot([lo, hi], [y, y], color=color, linewidth=2, solid_capstyle="round")
        ax.plot(est, y, "o", color=color, markersize=7, markeredgecolor=SURFACE,
                markeredgewidth=1.5)
        digits = 1 if "um" in key else 3
        ax.annotate(f"{est:.{digits}f}", (est, y), xytext=(0, 7), textcoords="offset points",
                    ha="center", fontsize=8, color=INK)
    ax.set_yticks(ys)
    ax.set_yticklabels(names)
    ax.set_ylim(-0.6, len(names) - 0.3)
    ax.grid(axis="y", visible=False)
    ax.set_title(LABELS.get(key, key))
    if "um" not in key:
        lo_lim = min(0.5, ax.get_xlim()[0]) if "rate" not in key else 0
        ax.set_xlim(lo_lim, 1.0 if "rate" not in key else max(0.3, ax.get_xlim()[1]))
    else:
        ax.set_xlim(0, None)


def plot_metrics(res, out):
    keys = ("PQ", "recall", "dice_per_gt", "dice_matched", "hd95_um_mean", "merge_rate")
    names = ["Pooled"] + list(res["per_slide"])
    metrics = [res["pooled"]] + [s["metrics"] for s in res["per_slide"].values()]
    ns = [res["counts"]["n_gt"]] + [s["counts"]["n_gt"] for s in res["per_slide"].values()]
    names = [f"{n}  (n={k})" for n, k in zip(names, ns)]
    fig, axes = plt.subplots(2, 3, figsize=(12, 1.6 + 0.9 * len(names)), sharey=True)
    for ax, k in zip(axes.ravel(), keys):
        _forest(ax, names, metrics, k)
    fig.suptitle("Benchmark metrics — point estimate and 95% interval "
                 "(cluster bootstrap over tiles, within-slide only)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, out / "metrics.png")


def plot_groups(res, key, title, out, fname):
    groups = res.get(key) or {}
    if not groups:
        return
    keys = ("recall", "dice_per_gt", "hd95_um_mean", "merge_rate")
    names = [f"{g.replace('tubule_', '')}  (n={v['n_gt']})" for g, v in groups.items()]
    fig, axes = plt.subplots(1, 4, figsize=(13, 1.4 + 0.55 * len(names)), sharey=True)
    for ax, k in zip(axes, keys):
        _forest(ax, names, [v["metrics"] for v in groups.values()], k)
    fig.suptitle(title, x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    save(fig, out / fname)


def plot_failure_types(objs, out):
    gts = [o for o in objs if o["status"] != "FP"]
    c = Counter(o["failure"] for o in objs)
    order = [k for k in ("merge", "leak", "split", "miss", "poor_overlap", "fp_on_object",
                         "fp_on_background") if c.get(k)]
    names = {"merge": "Merged with a neighbour", "leak": "Matched, but leaking",
             "split": "Split into pieces", "miss": "Missed entirely",
             "poor_overlap": "Poor overlap (IoU ≤ 0.5)",
             "fp_on_object": "Extra prediction on an object",
             "fp_on_background": "Extra prediction on background"}
    fig, ax = plt.subplots(figsize=(8, 0.9 + 0.42 * len(order)))
    ys = np.arange(len(order))[::-1]
    vals = [c[k] for k in order]
    ax.barh(ys, vals, height=0.62, color=BLUE)
    for y, k, v in zip(ys, order, vals):
        share = f"  ({v / len(gts):.1%} of annotated)" if not k.startswith("fp") else ""
        ax.text(v, y, f"  {v}{share}", va="center", fontsize=8.5, color=INK)
    ax.set_yticks(ys)
    ax.set_yticklabels([names[k] for k in order])
    ax.set_xlim(0, max(vals) * 1.45)
    ax.set_xlabel("objects")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"What goes wrong — {c.get('ok', 0)} of {len(gts)} annotated objects "
                 f"({c.get('ok', 0) / len(gts):.0%}) have no issue")
    fig.tight_layout()
    save(fig, out / "failure_types.png")


def plot_dice_vs_hd95(objs, out):
    tps = [o for o in objs if o["status"] == "TP" and math.isfinite(o["hd95_um"])]
    groups = (("ok", GREY, "o", "no issue"), ("leak", BLUE, "s", "leak"),
              ("merge", ORANGE, "^", "merge"), ("split", AQUA, "D", "split"))
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for key, color, marker, label in groups:
        g = [o for o in tps if o["failure"] == key]
        if g:
            ax.scatter([o["dice"] for o in g], [max(o["hd95_um"], 0.2) for o in g], s=26,
                       c=color, marker=marker, edgecolors=SURFACE, linewidths=0.6,
                       alpha=0.9 if key != "ok" else 0.55, label=f"{label} ({len(g)})",
                       zorder=3 if key != "ok" else 2)
    ax.set_yscale("log")
    ax.set_xlabel("Dice (matched objects)")
    ax.set_ylabel("HD95 (µm, log scale)")
    ax.set_title("Dice against HD95, one point per matched object — flagged objects carry\n"
                 "a large HD95 at Dice values that still count as a match")
    ax.legend(frameon=False, loc="upper right", title="object flagged as")
    fig.tight_layout()
    save(fig, out / "dice_vs_hd95.png")


def plot_distributions(objs, out):
    gts = [o for o in objs if o["status"] != "FP"]
    hd = np.array([o["hd95_um"] for o in gts if math.isfinite(o["hd95_um"])])
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.8))
    dice = np.array([o["dice"] for o in gts])
    a.hist(dice, bins=np.linspace(0, 1, 26), color=BLUE, edgecolor=SURFACE, linewidth=1)
    a.set_xlabel("Dice per annotated object")
    a.set_ylabel("objects")
    a.set_title(f"Dice — {int((dice == 0).sum())} unmatched objects sit at 0; "
                f"mean {dice.mean():.3f}")
    bins = np.logspace(np.log10(0.2), np.log10(max(hd.max(), 1) * 1.05), 28)
    b.hist(np.clip(hd, 0.2, None), bins=bins, color=BLUE, edgecolor=SURFACE, linewidth=1)
    b.set_xscale("log")
    for v, name in ((np.median(hd), "median"), (hd.mean(), "mean")):
        b.axvline(v, color=INK, linewidth=1, linestyle=":" if name == "median" else "-")
        b.text(v, b.get_ylim()[1] * 0.97, f" {name} {v:.1f}", fontsize=8, va="top", color=INK)
    b.set_xlabel("HD95 (µm, log scale; matched objects)")
    b.set_title("HD95 — a long tail pulls the mean above the median")
    for ax in (a, b):
        ax.grid(axis="x", visible=False)
    fig.tight_layout()
    save(fig, out / "distributions.png")


def plot_size_quartiles(res, out):
    q = res["edge_cases"].get("by_gt_area_quartile") or []
    if not q:
        return
    keys = (("recall", "Recall"), ("dice_per_gt", "Dice per annotated object"),
            ("hd95_um_mean", "HD95 mean (µm)"), ("merge_rate", "Merge rate"))
    names = [f"Q{r['quartile']}\n{r['area_px'][0]:.0f}–{r['area_px'][1]:.0f} px" for r in q]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.4))
    for ax, (k, label) in zip(axes, keys):
        vals = [r[k] if r[k] is not None else 0 for r in q]
        ax.bar(range(len(q)), vals, width=0.62, color=BLUE)
        for i, v in enumerate(vals):
            ax.text(i, v, f"{v:.2f}" if "um" not in k else f"{v:.1f}", ha="center",
                    va="bottom", fontsize=8.5, color=INK)
        ax.set_xticks(range(len(q)))
        ax.set_xticklabels(names, fontsize=7.5)
        ax.set_ylim(0, 1.08 if "um" not in k and "merge" not in k else max(vals) * 1.25)
        ax.grid(axis="x", visible=False)
        ax.set_title(label)
    fig.suptitle("By annotated object size (area quartiles; "
                 f"{q[0]['n']}–{q[-1]['n']} objects each)", x=0.01, ha="left", fontsize=11,
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, out / "size_quartiles.png")


def plot_tile_map(res, tiles, out, min_objects=3):
    slides = list(res["per_slide"])
    fig, axes = plt.subplots(1, len(slides), figsize=(6.2 * len(slides), 5.4), squeeze=False)
    size = res["provenance"]["tile_px"]
    for ax, sid in zip(axes[0], slides):
        ts = [t for t in tiles if t["slide"] == sid and int(t["n_gt"]) >= 1]
        for t in ts:
            x, y, n = int(t["x0"]), int(t["y0"]), int(t["n_gt"])
            d = _float(t["dice_per_gt"])
            ranked = n >= min_objects
            ax.add_patch(plt.Rectangle((x, y), size, size, facecolor=SEQ(1 - d) if ranked
                                       else "none", edgecolor=SURFACE if ranked else GREY,
                                       linewidth=1.5 if ranked else 0.6))
            if ranked:
                ax.text(x + size / 2, y + size / 2, f"{d:.2f}", ha="center", va="center",
                        fontsize=6.5, color="white" if d < 0.75 else INK)
        for (x0, y0, x1, y1) in res["provenance"]["slides"][sid]["rectangles"]:
            ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False,
                                       edgecolor=INK2, linewidth=0.8, linestyle=":"))
        xs = [int(t["x0"]) for t in ts]
        ys = [int(t["y0"]) for t in ts]
        ax.set_xlim(min(xs) - size, max(xs) + 2 * size)
        ax.set_ylim(max(ys) + 2 * size, min(ys) - size)
        ax.set_aspect("equal")
        ax.grid(False)
        ax.set_xlabel("x (working px)")
        ax.set_ylabel("y (working px)")
        ax.set_title(sid)
    sm = plt.cm.ScalarMappable(cmap=SEQ.reversed(), norm=plt.Normalize(0, 1))
    fig.colorbar(sm, ax=axes.ravel().tolist(), shrink=0.7, pad=0.02,
                 label="Dice per annotated object (darker = worse)")
    fig.suptitle(f"Where the low-scoring tiles are — tiles with ≥ {min_objects} annotated "
                 "objects are filled; outlined tiles have fewer", x=0.01, ha="left",
                 fontsize=11, fontweight="bold")
    save(fig, out / "tile_map.png")


def plot_stain_drift(res, out):
    d = res["edge_cases"].get("stain_drift")
    if not d:
        return
    lv = {v["level"]: v for v in d["levels"]}
    keys = (("PQ", "PQ against annotations"), ("dice_per_gt", "Dice per annotated object"),
            ("pq_vs_unperturbed_prediction", "PQ against the unperturbed prediction"))
    series = (("both", BLUE, "o", "-", "H and E together"), ("H", ORANGE, "s", "--", "H only"),
              ("E", AQUA, "^", ":", "E only"))
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9), sharey=True)
    for ax, (k, label) in zip(axes, keys):
        for prefix, color, marker, ls, name in series:
            pts = sorted((v["h_scale"] if prefix != "E" else v["e_scale"], v[k])
                         for n, v in lv.items() if n.startswith(prefix + "-")
                         or n.startswith(prefix + "+"))
            pts.append((1.0, lv["roundtrip"][k]))
            pts.sort()
            ax.plot(*zip(*pts), color=color, marker=marker, linestyle=ls, linewidth=2,
                    markersize=6, markeredgecolor=SURFACE, label=name)
        ax.axvspan(0.9, 1.1, color=GRID, alpha=0.6, zorder=0)
        ax.axhline(lv["baseline"][k], color=INK2, linewidth=1, linestyle="-")
        ax.set_xlabel("optical-density scale (1.0 = colour conversion only)")
        ax.set_title(label)
        ax.set_ylim(0.6, 1.02)
        ax.set_xticks([0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3])
    axes[0].text(0.905, 0.615, "training\njitter range", fontsize=7.5, color=INK2)
    axes[0].text(1.3, lv["baseline"]["PQ"] - 0.012, "line: untouched image", fontsize=7.5,
                 color=INK2, va="top", ha="right")
    axes[2].legend(frameon=False, loc="lower right")
    n = lv["baseline"]["n_gt"]
    fig.suptitle(f"Stain drift — synthetic haematoxylin / eosin scaling, {n} annotated "
                 "objects re-inferred per level", x=0.01, ha="left", fontsize=11,
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, out / "stain_drift.png")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bench-dir", required=True)
    p.add_argument("--n-examples", type=int, default=8)
    p.add_argument("--no-examples", action="store_true", help="charts only; no slide access")
    args = p.parse_args(argv)

    bench = Path(args.bench_dir)
    out = bench / "figures"
    out.mkdir(exist_ok=True)
    res = json.loads((bench / "benchmark.json").read_text())
    objs = load_objects(bench / "objects.csv")
    tiles = load_csv(bench / "tiles.csv")
    print(f"figures -> {out}")

    plot_metrics(res, out)
    plot_groups(res, "by_class", "By ground-truth class — estimate and 95% interval", out,
                "by_class.png")
    plot_groups(res, "by_source", "By annotation source — hand-drawn objects are the ones "
                "independent of the model", out, "by_source.png")
    plot_failure_types(objs, out)
    plot_dice_vs_hd95(objs, out)
    plot_distributions(objs, out)
    plot_size_quartiles(res, out)
    plot_tile_map(res, tiles, out)
    plot_stain_drift(res, out)
    if not args.no_examples:
        source = SlideSource(res)
        for kind in FAILURES:
            plot_examples(objs, source, kind, out, n=args.n_examples)
    return 0


if __name__ == "__main__":
    sys.exit(main())
