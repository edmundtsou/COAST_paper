#!/usr/bin/env python
"""Publication benchmark: score SAVED slide predictions against annotations.

    python scripts/benchmark_segmentation.py \
      --manifest data/manifest_mouse.csv --split val \
      --pred Ctrl_1A2_val=results/mouse_Ctrl_1A2 \
      --pred Nx_4wk_050=results/mouse_Nx_4wk_050 \
      --out-dir results/benchmark_mouse_val

Unlike eval_regions.py this never runs the model (except for --stain-drift): ``--pred`` is a
wsi_infer.py output directory, and its ``instance_map.npz`` is scored as it stands. The
class vocabulary, decode settings, tissue thresholds and ignore strategy are read from that
directory's ``summary.json``, i.e. from the checkpoint that produced the map, so they cannot
drift from the weights.

Each manifest row is scored over its ``roi`` rectangles, or over the bounding box of its
annotations when ``roi`` is blank. Objects are matched once on the uncut rectangle; the
``--tile`` grid only groups them, for the tile-level table and as the resampling unit of the
cluster bootstrap.

Written to --out-dir:

    objects.csv        one row per annotated object and per unmatched prediction
    tiles.csv          one row per tile
    slides.csv         one row per slide, with confidence intervals
    benchmark.json     everything above pooled, plus edge-case results and provenance
    failure_report.md  worst tiles and objects, ranked, with slide coordinates
    crops/             overlays of the worst tiles (--save-crops)

Metric definitions live in kidney_panoptic/eval/{matching,surface_metrics,benchmark}.py and
are restated in benchmark.json under "conventions".
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import _bootstrap  # noqa: F401
import cv2
import numpy as np

from kidney_panoptic.data.classes import ClassSpec
from kidney_panoptic.data.manifest import load_manifest
from kidney_panoptic.data.patching import parse_rois
from kidney_panoptic.data.tissue import build_tissue_mask
from kidney_panoptic.data.wsi import WSIReader
from kidney_panoptic.eval.benchmark import (
    LEAK_FRAC_FLAG, SOLIDITY_FLAG, class_lut, make_pooler, pooled_counts,
    prediction_integrity, score_rect, tile_confusions, tile_statistics,
)
from kidney_panoptic.eval.bootstrap import (
    MIN_UNITS_FOR_SE, between_unit_summary, cluster_bootstrap,
)
from kidney_panoptic.eval.ground_truth import (
    annotation_bounds, load_slide_annotations, rasterize_rect, rect_valid_mask,
)
from kidney_panoptic.eval.matching import match_instances, pq_from_counts
from kidney_panoptic.utils.config import apply_overrides

HEADLINE = ("PQ", "SQ", "DQ", "recall", "precision", "dice_per_gt", "iou_per_gt",
            "dice_matched", "iou_matched", "hd95_um_mean", "hd95_um_median", "hd95_px_mean",
            "assd_um_mean", "split_rate", "merge_rate", "fg_dice_px", "fg_iou_px")
SUBSET = ("recall", "dice_per_gt", "iou_per_gt", "dice_matched", "hd95_um_mean",
          "hd95_um_median", "split_rate", "merge_rate")

CONVENTIONS = {
    "matching": "class-agnostic; a pair is a true positive iff IoU > 0.5 (strict). Unique "
                "above 0.5, so identical to the Hungarian matching of panoptic_quality.",
    "iou": "|G n P| / |G u P| per matched pair",
    "dice": "2|G n P| / (|G| + |P|) per matched pair",
    "dice_per_gt / iou_per_gt": "mean over ALL annotated objects, unmatched objects count 0",
    "dice_matched / iou_matched": "mean over true positives only; conditioned on IoU > 0.5, "
                                  "so bounded below by 0.667 / 0.5",
    "surface": "outer contour: holes filled, then mask pixels with a 4-neighbour outside; "
               "pixels on the evaluation-rectangle edge are excluded. Overlap metrics are "
               "not hole-filled",
    "hd95": "max of the two directed 95th-percentile surface distances (MONAI / DeepMind "
            "surface-distance convention, not MedPy's pooled percentile); linear "
            "interpolation; true positives only, never imputed for misses",
    "assd": "sum of both directed surface distances over the total number of surface pixels",
    "leak_frac": "share of a matched prediction lying more than 5 px outside its annotation",
    "split / merge": "ground-truth object covered >= 20 % by two or more predictions / by a "
                     "prediction that also covers >= 20 % of another object",
    "fg_dice_px / fg_iou_px": "foreground pixels inside the valid mask, pooled by summing "
                              "counts over tiles",
    "ignore": "predictions with < 50 % of their area in the valid mask are dropped; "
              "predictions on trusted background are false positives (ADR 0003)",
    "confidence_interval": "percentile cluster bootstrap over tiles, stratified by slide; "
                           "every replicate recomputes the pooled statistic from counts",
}

CI_SCOPE = ("Confidence intervals describe spatial sampling variability WITHIN the scored "
            "slides. They do not describe generalisation across animals, sections, stain "
            "batches or scanners: with fewer than {n} slides the between-slide variance is "
            "not estimable and no between-slide standard error is reported."
            ).format(n=MIN_UNITS_FOR_SE)

# What each evaluation slide can and cannot support, from METHODS_AUDIT.md. Printed into the
# outputs so the numbers never travel without them.
KNOWN_CAVEATS = {
    "Nx_4wk_050": "Nx_4wk_050 supplied most of the patches used to select the checkpoint "
                  "(validation PQ). Results on it are validation results, not results on an "
                  "independent test set.",
    "Ctrl_1A2_val": "Ctrl_1A2_val is a set of held-out blocks of a section whose other "
                    "blocks were used for training. Pixels are disjoint; the section, stain "
                    "run and scan are shared.",
    "HUK1_COR_1_human_val": "HUK1_COR_1_human_val is held-out blocks of the training "
                            "section, and most of its objects are curated model output "
                            "(selected, not corrected) rather than hand-drawn. See the "
                            "by-source breakdown; the hand-drawn subset is the one that is "
                            "independent of the model's own boundary bias.",
}

# Controlled stain perturbations: (name, haematoxylin scale, eosin scale) applied to the
# optical-density channels. Training jitter draws each scale from U(0.9, 1.1), so +-0.1 is
# the edge of what the model was trained on and +-0.3 is three times beyond it.
DRIFT_LEVELS = (
    ("baseline", 1.0, 1.0),
    ("roundtrip", 1.0, 1.0),
    ("both-0.3", 0.7, 0.7), ("both-0.2", 0.8, 0.8), ("both-0.1", 0.9, 0.9),
    ("both+0.1", 1.1, 1.1), ("both+0.2", 1.2, 1.2), ("both+0.3", 1.3, 1.3),
    ("H-0.3", 0.7, 1.0), ("H+0.3", 1.3, 1.0), ("E-0.3", 1.0, 0.7), ("E+0.3", 1.0, 1.3),
)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest", required=True)
    p.add_argument("--split", default="val")
    p.add_argument("--pred", action="append", required=True, metavar="SLIDE_ID=DIR",
                   help="wsi_infer.py output directory for a manifest row; repeatable")
    p.add_argument("--roi", action="append", default=[], metavar="SLIDE_ID=x0,y0,x1,y1;...",
                   help="override the manifest roi for one row (working px)")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--tile", type=int, default=1024,
                   help="tile size in working px: table unit and bootstrap cluster")
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=1337)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--worst-k", type=int, default=20)
    p.add_argument("--min-tile-objects", type=int, default=3,
                   help="tiles with fewer annotated objects are not ranked")
    p.add_argument("--save-crops", action="store_true")
    p.add_argument("--stain-drift", action="store_true",
                   help="re-infer under controlled stain perturbation (needs --checkpoint)")
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--gpu", type=int, default=None)
    p.add_argument("--drift-size", type=int, default=2048)
    p.add_argument("--drift-regions", type=int, default=3)
    p.add_argument("--set", nargs="*", dest="overrides", default=[])
    return p.parse_args(argv)


def _pairs(items, flag):
    out = {}
    for it in items:
        if "=" not in it:
            raise SystemExit(f"{flag} expects SLIDE_ID=VALUE, got '{it}'")
        k, v = it.split("=", 1)
        out[k.strip()] = v.strip()
    return out


# ------------------------------------------------------------------ slide setup
def load_prediction(pred_dir: Path, overrides) -> dict:
    with open(pred_dir / "summary.json") as f:
        summary = json.load(f)
    npz_path = pred_dir / "instance_map.npz"
    if not npz_path.exists():
        raise SystemExit(f"{npz_path} not found — rerun wsi_infer.py without --no-save-map")
    npz = np.load(npz_path)
    cfg = summary["config"]
    if overrides:
        apply_overrides(cfg, overrides)
    return {"dir": pred_dir, "summary": summary, "cfg": cfg,
            "spec": ClassSpec.from_config(cfg), "map": npz["instance_map"],
            "class_of_id": {int(i): int(c) for i, c in npz["class_of_id"]},
            "mpp": float(summary["working_mpp"]),
            "region": tuple(int(v) for v in summary["region"])}


def open_reader(row: dict, pred: dict) -> WSIReader:
    """Open the manifest image at the level the prediction was made on.

    The prediction may come from a flat export of the same level (the level-1 TIFFs) while
    the manifest names the pyramidal source, so the level is not taken on trust: whichever
    candidate level reproduces the prediction's slide size and resolution is used, and none
    matching is an error rather than a silently misregistered comparison.
    """
    want = tuple(pred["summary"]["slide_size_work"])
    wcfg = pred["cfg"].get("wsi", {})
    lvl, mpp = (row.get("level") or "").strip(), (row.get("manual_mpp") or "").strip()
    levels = [int(lvl)] if lvl else list(dict.fromkeys([wcfg.get("level", 1), 1, 0]))
    seen = []
    for lv in levels:
        try:
            r = WSIReader(row["image_path"], level=lv,
                          manual_mpp=float(mpp) if mpp else wcfg.get("manual_mpp"))
        except ValueError as e:
            seen.append(f"level {lv}: {e}")
            continue
        size = tuple(r.level_dimensions_work)
        if size == want and abs(r.working_mpp - pred["mpp"]) / pred["mpp"] < 0.02:
            return r
        seen.append(f"level {lv}: size {size}, mpp {r.working_mpp:.5f}")
        r.close()
    raise SystemExit(
        f"[{row['slide_id']}] {row['image_path']} does not match the prediction in "
        f"{pred['dir']} (slide size {want}, mpp {pred['mpp']:.5f}). Tried: {seen}")


def slide_rects(row, ann, roi_override, W, H):
    rects = parse_rois(roi_override if roi_override is not None else (row.get("roi") or ""))
    return rects or [annotation_bounds(ann, W, H)]


# -------------------------------------------------------------------- scoring
def score_slide(row, pred, args, roi_override, keep_arrays: bool):
    sid = row["slide_id"]
    cfg, spec = pred["cfg"], pred["spec"]
    reader = open_reader(row, pred)
    W, H = reader.level_dimensions_work
    to_work = 1.0 if cfg["patch"].get("annotations_space", "full") == "level" \
        else reader.scale_full_to_work
    ann = load_slide_annotations(row["geojson_path"], spec, to_work)
    rects = slide_rects(row, ann, roi_override, W, H)
    px0, py0, pw, ph = pred["region"]
    names = list(spec.names)
    lut_pred = class_lut(pred["class_of_id"], int(pred["map"].max()))

    records, tiles, contexts = [], {}, []
    integrity = Counter()
    stray = []
    print(f"\n[{sid}] {len(ann.polys)} annotated objects, {len(rects)} rectangle(s), "
          f"prediction {pred['dir']}")
    for ri, rect in enumerate(rects):
        x0, y0, x1, y1 = rect
        if x0 < px0 or y0 < py0 or x1 > px0 + pw or y1 > py0 + ph:
            raise SystemExit(f"[{sid}] rectangle {rect} is outside the predicted region "
                             f"{pred['region']}")
        rgb = reader.read_region_work(x0, y0, x1 - x0, y1 - y0)
        tissue = build_tissue_mask(rgb, cfg.get("tissue"))
        gt, gt_class, gt_meta = rasterize_rect(ann, spec, rect)
        valid = rect_valid_mask(gt, tissue, ann, rect, cfg)
        pm = np.ascontiguousarray(pred["map"][y0 - py0:y1 - py0, x0 - px0:x1 - px0])

        recs = score_rect(gt, pm, valid, gt_class=gt_class, pred_class=pred["class_of_id"],
                          class_names=names, mpp=pred["mpp"], origin_xy=(x0, y0),
                          gt_meta=gt_meta,
                          leak_tolerance_px=float(cfg.get("annotation", {})
                                                  .get("dilate_px_inner", 5)))
        confs = tile_confusions(class_lut(gt_class, int(gt.max()))[gt], lut_pred[pm], valid,
                                len(names), args.tile)
        by_tile = defaultdict(list)
        for r in recs:
            tx, ty = int((r["cx"] - x0) // args.tile), int((r["cy"] - y0) // args.tile)
            r.update(slide=sid, rect=ri, tile_x=x0 + tx * args.tile, tile_y=y0 + ty * args.tile)
            by_tile[(tx, ty)].append(r)
        for key in sorted(set(by_tile) | set(confs)):
            tx, ty = key
            t = tile_statistics(by_tile.get(key, []), confs.get(key))
            t.update(slide=sid, rect=ri, x0=x0 + tx * args.tile, y0=y0 + ty * args.tile)
            if t["tp"] + t["fn"]:
                t.update(_stain_od(rgb, tissue, tx, ty, args.tile))
            tiles[(sid, ri, tx, ty)] = t
        records += recs

        integ = prediction_integrity(pm, pred["class_of_id"], names,
                                     cfg.get("decode", {}).get("min_area", {}) or {})
        for k in ("n_instances", "n_below_min_area", "n_multi_component"):
            integrity[k] += integ[k]
        if integ["n_multi_component"]:
            stray.append((integ["mean_stray_area_frac"], integ["n_multi_component"]))

        n_gt = sum(r["status"] != "FP" for r in recs)
        print(f"  rect {ri} {rect}: {n_gt} GT, TP {sum(r['status'] == 'TP' for r in recs)} "
              f"FP {sum(r['status'] == 'FP' for r in recs)} "
              f"FN {sum(r['status'] == 'FN' for r in recs)}, valid {valid.mean() * 100:.1f}%")
        if keep_arrays:
            contexts.append({"rect": rect, "rgb": rgb, "gt": gt, "pred": pm, "valid": valid,
                             "tissue": tissue, "gt_class": gt_class, "gt_meta": gt_meta})

    integ_out = dict(integrity)
    integ_out["mean_stray_area_frac"] = float(
        sum(f * n for f, n in stray) / sum(n for _, n in stray)) if stray else 0.0
    return {"records": records, "tiles": tiles, "integrity": integ_out,
            "contexts": contexts, "reader": reader, "ann": ann, "rects": rects}


def _stain_od(rgb, tissue, tx, ty, tile) -> dict:
    """Mean haematoxylin and eosin optical density over the tile's tissue pixels."""
    from skimage.color import rgb2hed

    sl = (slice(ty * tile, (ty + 1) * tile), slice(tx * tile, (tx + 1) * tile))
    t = tissue[sl]
    if not t.any():
        return {"h_od": float("nan"), "e_od": float("nan")}
    hed = rgb2hed(rgb[sl].astype(np.float32) / 255.0)
    return {"h_od": float(hed[..., 0][t].mean()), "e_od": float(hed[..., 1][t].mean())}


# ----------------------------------------------------------------- summaries
def summarize(tiles, class_names, args, keys, strata=None):
    stat = make_pooler(tiles, class_names)
    full = cluster_bootstrap(len(tiles), stat, strata=strata, n_boot=args.n_boot,
                             seed=args.seed, alpha=args.alpha)
    keep = set(keys) | {k for k in full if k.startswith("dice_px[")}
    return {k: v for k, v in full.items() if k in keep}


def subset_tiles(all_keys, records, keep):
    by = defaultdict(list)
    for r in records:
        if keep(r):
            by[(r["slide"], r["rect"], r["tile_x"], r["tile_y"])].append(r)
    return [tile_statistics(by.get(k, [])) for k in all_keys]


def edge_cases(records, tiles, integrity, class_names, args):
    gts = [r for r in records if r["status"] != "FP"]
    tps = [r for r in gts if r["status"] == "TP"]
    fps = [r for r in records if r["status"] == "FP"]

    def col(rows, k):
        v = np.array([r[k] for r in rows], float)
        return v[np.isfinite(v)]

    def rate(v, cond):
        return float(cond(v).mean()) if v.size else None

    def mean(v):
        return float(v.mean()) if v.size else None

    leak = col(tps, "leak_frac")
    asym = col(tps, "h95_pred_to_gt_px") - col(tps, "h95_gt_to_pred_px")
    ratio = col(tps, "area_ratio")
    conf = sum(t["conf"] for t in tiles if t["conf"] is not None)
    pred_fg = int(conf[:, 1:].sum())
    out = {"boundary_leakage": {
        "n_matched": len(tps),
        "leak_frac_mean": mean(leak),
        f"leak_frac_gt_{LEAK_FRAC_FLAG}_rate": rate(leak, lambda v: v > LEAK_FRAC_FLAG),
        "over_reach_asymmetry_px_mean": mean(asym),
        "over_reach_asymmetry_px_median": float(np.median(asym)) if asym.size else None,
        "area_ratio_median": float(np.median(ratio)) if ratio.size else None,
        "area_ratio_mean": mean(ratio),
        f"pred_solidity_lt_{SOLIDITY_FLAG}_rate":
            rate(col(tps, "pred_solidity"), lambda v: v < SOLIDITY_FLAG),
        f"gt_solidity_lt_{SOLIDITY_FLAG}_rate":
            rate(col(gts, "gt_solidity"), lambda v: v < SOLIDITY_FLAG),
        "pred_px_on_trusted_background_frac":
            float(conf[0, 1:].sum() / pred_fg) if pred_fg else None,
    }}

    multi = [r for r in tps + fps if (r["n_components"] or 0) > 1]
    fp_area = col(fps, "pred_area")
    out["small_and_disconnected"] = {
        "scored_predictions": len(tps) + len(fps),
        "scored_multi_component": len(multi),
        "all_predictions_in_rectangles": integrity,
        "false_positives": {
            "n": len(fps),
            "on_object": sum(r["failure"] == "fp_on_object" for r in fps),
            "on_background": sum(r["failure"] == "fp_on_background" for r in fps),
            "area_px_quartiles": [float(q) for q in np.percentile(fp_area, [25, 50, 75])]
            if fp_area.size else None,
        },
    }

    areas = col(gts, "gt_area")
    strata = []
    if areas.size >= 8:
        edges = np.percentile(areas, [0, 25, 50, 75, 100])
        for q in range(4):
            lo, hi = edges[q], edges[q + 1]
            rows = [r for r in gts if (lo <= r["gt_area"] <= hi if q == 3
                                       else lo <= r["gt_area"] < hi)]
            t = [r for r in rows if r["status"] == "TP"]
            strata.append({"quartile": q + 1, "area_px": [float(lo), float(hi)],
                           "n": len(rows), "recall": len(t) / len(rows) if rows else None,
                           "dice_per_gt": mean(col(rows, "dice")),
                           "hd95_um_mean": mean(col(t, "hd95_um")),
                           "merge_rate": float(np.mean([r["merged"] for r in rows]))
                           if rows else None})
    out["by_gt_area_quartile"] = strata

    inner = [r for r in tps if not r["touches_border"]]
    out["border_sensitivity"] = {
        "n_matched_touching_rectangle_edge": len(tps) - len(inner),
        "hd95_um_mean_all": mean(col(tps, "hd95_um")),
        "hd95_um_mean_excluding_edge_objects": mean(col(inner, "hd95_um")),
    }

    agree = Counter((r["gt_class"], r["pred_class"]) for r in tps)
    out["class_agreement_among_matched"] = {
        "accuracy": (sum(n for (g, p), n in agree.items() if g == p) / len(tps))
        if tps else None,
        "confusion": [{"gt": g, "pred": p, "n": n} for (g, p), n in sorted(agree.items())],
    }
    out["stain_observational"] = stain_observational(tiles, args)
    return out


def stain_observational(tiles, args):
    """Does segmentation quality track staining intensity across the tiles as scanned?

    Observational only: staining intensity is confounded with anatomy (medulla stains
    differently from cortex), so an association here is not evidence of stain sensitivity
    on its own. The controlled test is --stain-drift.
    """
    from scipy import stats

    stat = make_pooler(tiles)
    rows = []
    for i, t in enumerate(tiles):
        if t["tp"] + t["fn"] >= args.min_tile_objects and np.isfinite(t.get("h_od", np.nan)):
            s = stat(np.array([i]))
            rows.append((i, t["h_od"], t["e_od"], s["dice_per_gt"], s["hd95_um_mean"]))
    out = {"n_tiles": len(rows), "note": stain_observational.__doc__.split("\n\n")[1]
           .replace("\n    ", " ").strip()}
    if len(rows) < 6:
        out["skipped"] = "fewer than 6 tiles with enough annotated objects"
        return out
    a = np.array(rows, float)
    for ci, cname in ((1, "h_od"), (2, "e_od")):
        for mi, mname in ((3, "dice_per_gt"), (4, "hd95_um_mean")):
            ok = np.isfinite(a[:, mi])
            rho, p = stats.spearmanr(a[ok, ci], a[ok, mi]) if ok.sum() >= 6 else (None, None)
            out[f"spearman[{cname},{mname}]"] = {
                "rho": _num(rho), "p": _num(p), "n": int(ok.sum())}
        cuts = np.percentile(a[:, ci], [100 / 3, 200 / 3])
        tert = np.digitize(a[:, ci], cuts)
        out[f"tertiles[{cname}]"] = []
        for k in range(3):
            idx = a[tert == k, 0].astype(int)
            s = stat(idx) if len(idx) else {}
            out[f"tertiles[{cname}]"].append({
                "tertile": k + 1, "n_tiles": int(len(idx)),
                "od_mean": _num(a[tert == k, ci].mean()) if len(idx) else None,
                "dice_per_gt": _num(s.get("dice_per_gt")),
                "hd95_um_mean": _num(s.get("hd95_um_mean")), "PQ": _num(s.get("PQ"))})
    return out


# ---------------------------------------------------------------- stain drift
def scale_stain(rgb: np.ndarray, h: float, e: float) -> np.ndarray:
    """Scale the haematoxylin and eosin optical densities of an RGB image.

    The RGB -> HED -> RGB round trip is not exact (the inverse clips), so scales of 1.0
    still change pixels slightly. The "roundtrip" drift level measures that on its own, and
    is the reference the scaled levels should be read against.
    """
    from skimage.color import hed2rgb, rgb2hed

    hed = rgb2hed(rgb.astype(np.float32) / 255.0)
    hed[..., 0] *= h
    hed[..., 1] *= e
    return (np.clip(hed2rgb(hed), 0, 1) * 255.0).astype(np.uint8)


def pick_windows(rects, records, size, n):
    """Up to ``n`` windows of ``size`` px, each inside one rectangle, densest in objects first."""
    pts = np.array([[r["cx"], r["cy"]] for r in records if r["status"] != "FP"])
    used = np.zeros(len(pts), bool)
    picks = []
    for _ in range(n):
        best, best_in = None, None
        for (x0, y0, x1, y1) in rects:
            if x1 - x0 < size or y1 - y0 < size:
                continue
            for i in np.flatnonzero(~used):
                cx, cy = pts[i]
                if not (x0 <= cx < x1 and y0 <= cy < y1):
                    continue
                wx = int(np.clip(cx - size / 2, x0, x1 - size))
                wy = int(np.clip(cy - size / 2, y0, y1 - size))
                inside = (~used & (pts[:, 0] >= wx) & (pts[:, 0] < wx + size) &
                          (pts[:, 1] >= wy) & (pts[:, 1] < wy + size))
                if best_in is None or inside.sum() > best_in.sum():
                    best, best_in = (wx, wy, wx + size, wy + size), inside
        if best is None or not best_in.any():
            break
        picks.append(best)
        used |= best_in
    return picks


def stain_drift(slides, preds, args):
    """Re-infer evaluation windows under controlled stain perturbation and rescore them."""
    import torch

    from kidney_panoptic.infer.tiled import TiledPredictor, array_fetcher
    from kidney_panoptic.utils.checkpoint import build_from_checkpoint

    device = f"cuda:{args.gpu}" if args.gpu is not None else (
        "cuda" if torch.cuda.is_available() else "cpu")
    per_level = {name: {"tiles": [], "tissue": [], "cons": np.zeros(4)}
                 for name, _, _ in DRIFT_LEVELS}
    windows_used = {}
    model = None
    for sid, s in slides.items():
        pred = preds[sid]
        if model is None:
            model, ckpt_cfg, _ = build_from_checkpoint(args.checkpoint, device=device)
        # Decode and inference settings come from the scored prediction, so the guards and
        # TTA that produced the headline numbers are the ones under test here.
        cfg = dict(ckpt_cfg)
        for k in ("decode", "infer", "tissue"):
            if k in pred["cfg"]:
                cfg[k] = pred["cfg"][k]
        spec = pred["spec"]
        predictor = TiledPredictor(model, cfg, spec, device=device)
        wins = pick_windows(s["rects"], s["records"], args.drift_size, args.drift_regions)
        windows_used[sid] = wins
        print(f"\n[{sid}] stain drift on {len(wins)} window(s) of {args.drift_size}px")
        for rect in wins:
            x0, y0, x1, y1 = rect
            size = x1 - x0
            rgb = s["reader"].read_region_work(x0, y0, size, size)
            gt, gt_class, gt_meta = rasterize_rect(s["ann"], spec, rect)
            valid = rect_valid_mask(gt, build_tissue_mask(rgb, cfg.get("tissue")), s["ann"],
                                    rect, cfg)
            base_map = None
            for name, h, e in DRIFT_LEVELS:
                img = rgb if name == "baseline" else scale_stain(rgb, h, e)
                tissue = build_tissue_mask(img, cfg.get("tissue"))
                res, _ = predictor.predict_and_decode(array_fetcher(img), 0, 0, size, size,
                                                      size, size, tissue=tissue)
                recs = score_rect(gt, res.id_map, valid, gt_class=gt_class,
                                  pred_class=res.class_of_id, class_names=list(spec.names),
                                  mpp=pred["mpp"], origin_xy=(x0, y0), gt_meta=gt_meta)
                lv = per_level[name]
                lv["tiles"].append(tile_statistics(recs))
                lv["tissue"].append(float(tissue.mean()))
                if name == "baseline":
                    base_map = res.id_map
                m = match_instances(base_map, res.id_map)
                lv["cons"] += (m.tp, m.fp, m.fn, m.sum_iou)
                t = lv["tiles"][-1]
                print(f"  {rect} {name:>9}: TP {t['tp']} FP {t['fp']} FN {t['fn']} "
                      f"tissue {tissue.mean() * 100:.0f}%")

    keys = ("PQ", "recall", "dice_per_gt", "hd95_um_mean", "merge_rate", "split_rate")
    levels = []
    for name, h, e in DRIFT_LEVELS:
        lv = per_level[name]
        if not lv["tiles"]:
            continue
        s = make_pooler(lv["tiles"])(np.arange(len(lv["tiles"])))
        c = pooled_counts(lv["tiles"])
        levels.append({"level": name, "h_scale": h, "e_scale": e,
                       **{k: _num(s[k]) for k in keys},
                       "n_gt": c["n_gt"], "n_pred": c["n_pred"],
                       "pq_vs_unperturbed_prediction": _num(pq_from_counts(*lv["cons"])["PQ"]),
                       "tissue_fraction": float(np.mean(lv["tissue"]))})
    return {
        "note": "Synthetic perturbation of the haematoxylin / eosin optical densities of "
                "held-out windows, re-inferred window-locally. Training augmentation draws "
                "each scale from U(0.9, 1.1); larger steps are outside it. The 'roundtrip' level "
                "applies the colour-space conversion with both scales at 1.0 and is the "
                "reference for the scaled levels: the conversion alone perturbs pixels. This measures "
                "sensitivity to stain STRENGTH on these sections; it is not evidence about "
                "other stains, protocols or scanners. The baseline differs slightly from the "
                "headline numbers because it is a window-local re-inference, not the "
                "slide-wide map.",
        "checkpoint": str(args.checkpoint), "window_px": args.drift_size,
        "windows": {k: [list(w) for w in v] for k, v in windows_used.items()},
        "levels": levels,
    }


# ------------------------------------------------------------------- outputs
def _num(v):
    if v is None:
        return None
    v = float(v)
    return v if math.isfinite(v) else None


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return _num(o)
    if isinstance(o, Path):
        return str(o)
    return o


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if (v := r.get(k)) is None or
                            (isinstance(v, float) and not math.isfinite(v)) else
                            (f"{v:.4f}" if isinstance(v, float) else v)) for k in fields})


OBJECT_FIELDS = ("slide", "rect", "tile_x", "tile_y", "status", "failure", "gt_id", "pred_id",
                 "gt_class", "pred_class", "raw_label", "source", "cx", "cy", "gt_area",
                 "pred_area", "iou", "dice", "best_iou", "hd95_um", "hd95_px",
                 "h95_gt_to_pred_px", "h95_pred_to_gt_px", "hd_px", "assd_um", "assd_px",
                 "leak_frac", "area_ratio", "gt_solidity", "pred_solidity", "n_components",
                 "stray_area_frac", "pred_on_gt_frac", "touches_border", "split", "merged")
TILE_FIELDS = ("slide", "rect", "x0", "y0", "size", "n_gt", "tp", "fp", "fn", "n_split",
               "n_merged", "PQ", "dice_per_gt", "dice_matched", "hd95_um_mean", "hd95_um_max",
               "assd_um_mean", "leak_frac_mean", "fg_dice_px", "fg_iou_px", "h_od", "e_od")


def tile_rows(tiles, class_names, tile):
    stat = make_pooler(tiles, class_names)
    rows = []
    for i, t in enumerate(tiles):
        s = stat(np.array([i]))
        rows.append({"slide": t["slide"], "rect": t["rect"], "x0": t["x0"], "y0": t["y0"],
                     "size": tile, "n_gt": t["tp"] + t["fn"], "tp": t["tp"], "fp": t["fp"],
                     "fn": t["fn"], "n_split": t["n_split"], "n_merged": t["n_merged"],
                     "hd95_um_max": float(t["hd95_um"].max()) if t["hd95_um"].size else None,
                     "h_od": t.get("h_od"), "e_od": t.get("e_od"),
                     **{k: s.get(k) for k in ("PQ", "dice_per_gt", "dice_matched",
                                              "hd95_um_mean", "assd_um_mean",
                                              "leak_frac_mean", "fg_dice_px", "fg_iou_px")}})
    return rows


def _ci(m, digits=3):
    if m is None or m.get("estimate") is None:
        return "n/a"
    s = f"{m['estimate']:.{digits}f}"
    if m.get("ci_low") is not None:
        s += f" [{m['ci_low']:.{digits}f}, {m['ci_high']:.{digits}f}]"
    return s


def _v(v, digits=3):
    return "n/a" if v is None or (isinstance(v, float) and not math.isfinite(v)) \
        else (f"{v:.{digits}f}" if isinstance(v, float) else str(v))


def _table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def write_report(path, res, trows, records, args):
    k, mn = args.worst_k, args.min_tile_objects
    pct = int(round(100 * (1 - args.alpha)))
    L = ["# Segmentation benchmark — failure report\n"]
    c = res["counts"]
    L.append(f"{c['n_gt']} annotated objects, {c['n_pred']} scored predictions, "
             f"{c['n_tiles']} tiles of {args.tile} px over {len(res['per_slide'])} slide(s). "
             f"TP {c['tp']} / FP {c['fp']} / FN {c['fn']}. Brackets are {pct}% intervals "
             f"({args.n_boot} bootstrap replicates over tiles).\n")
    L.append("**Read this first**\n")
    L += [f"- {t}" for t in res["caveats"]] + [""]

    L.append("## Pooled metrics\n")
    L.append(_table(["metric", f"estimate [{pct}% CI]"],
                    [(m, _ci(res["pooled"][m])) for m in HEADLINE if m in res["pooled"]] +
                    [(m, _ci(v)) for m, v in res["pooled"].items() if m.startswith("dice_px[")]))
    L.append("HD95 and ASSD are over true positives only; read them next to recall. "
             "`dice_per_gt` counts each missed object as 0, `dice_matched` does not.\n")

    cols = ("PQ", "recall", "dice_per_gt", "dice_matched", "hd95_um_mean", "merge_rate")
    L.append("## Per slide\n")
    L.append(_table(["slide", "n GT"] + list(cols),
                    [[sid, s["counts"]["n_gt"]] + [_ci(s["metrics"][m]) for m in cols]
                     for sid, s in res["per_slide"].items()]))
    L.append(res["between_slide"]["note"] + "\n")

    for title, key in (("By ground-truth class", "by_class"), ("By annotation source", "by_source")):
        if res.get(key):
            sc = ("recall", "dice_per_gt", "hd95_um_mean", "split_rate", "merge_rate")
            L.append(f"## {title}\n")
            L.append(_table(["group", "n GT"] + list(sc),
                            [[g, v["n_gt"]] + [_ci(v["metrics"][m]) for m in sc]
                             for g, v in res[key].items()]))

    L.append("## Failure types (annotated objects)\n")
    gts = [r for r in records if r["status"] != "FP"]
    ft = Counter(r["failure"] for r in gts)
    L.append(_table(["type", "n", "share"],
                    [(t, n, f"{100 * n / max(len(gts), 1):.1f}%") for t, n in ft.most_common()]))
    L.append("`merge` and `split` take precedence over the detection outcome; `miss` is an "
             "unmatched object whose best overlap is IoU < 0.10; `leak` is a matched object "
             f"with more than {LEAK_FRAC_FLAG:.0%} of the prediction beyond the 5 px ring.\n")

    ranked = [t for t in trows if t["n_gt"] >= mn]
    head = ["slide", "x0", "y0", "n GT", "TP/FP/FN", "dice_per_gt", "HD95 µm mean",
            "HD95 µm max", "merged", "split", "fg Dice px"]

    def trow(t):
        return [t["slide"], t["x0"], t["y0"], t["n_gt"], f"{t['tp']}/{t['fp']}/{t['fn']}",
                _v(t["dice_per_gt"]), _v(t["hd95_um_mean"], 2), _v(t["hd95_um_max"], 2),
                t["n_merged"], t["n_split"], _v(t["fg_dice_px"])]

    L.append(f"## Worst tiles by Dice (lowest `dice_per_gt`, tiles with ≥ {mn} objects)\n")
    L.append(_table(head, [trow(t) for t in sorted(
        [t for t in ranked if t["dice_per_gt"] is not None],
        key=lambda t: t["dice_per_gt"])[:k]]))
    L.append(f"## Worst tiles by HD95 (highest mean, tiles with ≥ {mn} matched objects)\n")
    L.append(_table(head, [trow(t) for t in sorted(
        [t for t in ranked if t["tp"] >= mn and t["hd95_um_mean"] is not None],
        key=lambda t: -t["hd95_um_mean"])[:k]]))
    L.append(f"{len(ranked)} of {len(trows)} tiles have ≥ {mn} annotated objects and are "
             "ranked. Coordinates are the tile's top-left corner in working pixels.\n")

    ohead = ["slide", "cx", "cy", "class", "status", "failure", "Dice", "HD95 µm",
             "pred→GT px", "GT→pred px", "leak", "area ratio"]

    def orow(r):
        return [r["slide"], int(r["cx"]), int(r["cy"]), r["gt_class"] or r["pred_class"],
                r["status"], r["failure"], _v(r["dice"]), _v(r["hd95_um"], 2),
                _v(r["h95_pred_to_gt_px"], 1), _v(r["h95_gt_to_pred_px"], 1),
                _v(r["leak_frac"]), _v(r["area_ratio"], 2)]

    tps = [r for r in gts if r["status"] == "TP" and math.isfinite(r["hd95_um"])]
    L.append("## Worst matched objects by HD95\n")
    L.append(_table(ohead, [orow(r) for r in sorted(tps, key=lambda r: -r["hd95_um"])[:k]]))
    L.append("## Worst matched objects by leak fraction\n")
    L.append(_table(ohead, [orow(r) for r in sorted(
        [r for r in tps if math.isfinite(r["leak_frac"])], key=lambda r: -r["leak_frac"])[:k]]))
    fns = sorted([r for r in gts if r["status"] == "FN"], key=lambda r: -r["gt_area"])
    L.append(f"## Unmatched annotated objects ({len(fns)}; largest first)\n")
    L.append(_table(["slide", "cx", "cy", "class", "failure", "area px", "best IoU"],
                    [[r["slide"], int(r["cx"]), int(r["cy"]), r["gt_class"], r["failure"],
                      r["gt_area"], _v(r["best_iou"])] for r in fns[:k]]))

    ec = res["edge_cases"]
    L.append("## Edge cases\n")
    L.append("### Boundary leakage\n")
    L.append(_table(["quantity", "value"], [(a, _v(b)) for a, b in ec["boundary_leakage"].items()]))
    L.append("### Small and disconnected components\n")
    sd = ec["small_and_disconnected"]
    ai, fp = sd["all_predictions_in_rectangles"], sd["false_positives"]
    L.append(_table(["quantity", "value"], [
        ("predictions inside the rectangles (not edge-cut)", ai.get("n_instances", 0)),
        ("  below their class min_area floor", ai.get("n_below_min_area", 0)),
        ("  with more than one connected component", ai.get("n_multi_component", 0)),
        ("  mean stray area share among those", _v(ai.get("mean_stray_area_frac"))),
        ("false positives", fp["n"]),
        ("  fragments on an annotated object", fp["on_object"]),
        ("  on trusted background", fp["on_background"]),
        ("  area px, quartiles", fp["area_px_quartiles"])]))
    if ec["by_gt_area_quartile"]:
        L.append("### By ground-truth size\n")
        L.append(_table(["quartile", "area px", "n", "recall", "dice_per_gt", "HD95 µm", "merge"],
                        [[q["quartile"], f"{q['area_px'][0]:.0f}–{q['area_px'][1]:.0f}", q["n"],
                          _v(q["recall"]), _v(q["dice_per_gt"]), _v(q["hd95_um_mean"], 2),
                          _v(q["merge_rate"])] for q in ec["by_gt_area_quartile"]]))
    so = ec["stain_observational"]
    L.append("### Stain intensity (observational)\n")
    L.append(so["note"] + "\n")
    if "skipped" in so:
        L.append(f"Skipped: {so['skipped']}.\n")
    else:
        L.append(_table(["pair", "Spearman ρ", "p", "n tiles"],
                        [[key[9:-1], _v(v["rho"]), _v(v["p"]), v["n"]]
                         for key, v in so.items() if key.startswith("spearman[")]))
        for ch in ("h_od", "e_od"):
            L.append(_table([f"{ch} tertile", "mean OD", "n tiles", "PQ", "dice_per_gt", "HD95 µm"],
                            [[t["tertile"], _v(t["od_mean"]), t["n_tiles"], _v(t["PQ"]),
                              _v(t["dice_per_gt"]), _v(t["hd95_um_mean"], 2)]
                             for t in so[f"tertiles[{ch}]"]]))
    if "stain_drift" in ec:
        d = ec["stain_drift"]
        L.append("### Stain drift (controlled perturbation)\n")
        L.append(d["note"] + "\n")
        L.append(_table(["level", "H×", "E×", "PQ", "recall", "dice_per_gt", "HD95 µm", "merge",
                         "n pred", "PQ vs unperturbed", "tissue"],
                        [[v["level"], v["h_scale"], v["e_scale"], _v(v["PQ"]), _v(v["recall"]),
                          _v(v["dice_per_gt"]), _v(v["hd95_um_mean"], 2), _v(v["merge_rate"]),
                          v["n_pred"], _v(v["pq_vs_unperturbed_prediction"]),
                          _v(v["tissue_fraction"])] for v in d["levels"]]))
    Path(path).write_text("\n".join(L))


def save_crops(out_dir, slides, trows, args):
    """Overlay per worst tile: annotation in green, scored prediction in red, ignored dimmed."""
    from skimage.segmentation import find_boundaries

    ranked = [t for t in trows if t["n_gt"] >= args.min_tile_objects]
    worst = sorted([t for t in ranked if t["dice_per_gt"] is not None],
                   key=lambda t: t["dice_per_gt"])[:args.worst_k]
    worst += sorted([t for t in ranked if t["hd95_um_mean"] is not None],
                    key=lambda t: -t["hd95_um_mean"])[:args.worst_k]
    out_dir.mkdir(parents=True, exist_ok=True)
    done = set()
    for t in worst:
        key = (t["slide"], t["rect"], t["x0"], t["y0"])
        if key in done:
            continue
        done.add(key)
        c = slides[t["slide"]]["contexts"][t["rect"]]
        x0, y0 = c["rect"][:2]
        sl = (slice(t["y0"] - y0, t["y0"] - y0 + args.tile),
              slice(t["x0"] - x0, t["x0"] - x0 + args.tile))
        img = c["rgb"][sl].copy()
        img[~c["valid"][sl]] = (0.5 * img[~c["valid"][sl]] + 96).astype(np.uint8)
        img[find_boundaries(c["gt"][sl], mode="inner")] = (0, 220, 0)
        img[find_boundaries(c["pred"][sl], mode="inner")] = (230, 30, 30)
        cv2.imwrite(str(out_dir / f"{t['slide']}_x{t['x0']}_y{t['y0']}.png"),
                    cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    print(f"crops -> {out_dir} ({len(done)} tiles)")


def _git():
    try:
        root = Path(__file__).resolve().parents[1]
        rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                                    cwd=root, capture_output=True, text=True).stdout.strip())
        return {"commit": rev, "tracked_files_modified": dirty}
    except Exception:
        return {"commit": None}


# ----------------------------------------------------------------------- main
def main(argv=None):
    args = parse_args(argv)
    if args.stain_drift and not args.checkpoint:
        raise SystemExit("--stain-drift needs --checkpoint")
    pred_dirs, roi_over = _pairs(args.pred, "--pred"), _pairs(args.roi, "--roi")
    rows = load_manifest(args.manifest, splits=(args.split,))
    unknown = set(pred_dirs) - {r["slide_id"] for r in rows}
    if unknown:
        raise SystemExit(f"--pred names slide(s) not in the {args.split} split of "
                         f"{args.manifest}: {sorted(unknown)}")
    skipped = [r["slide_id"] for r in rows if r["slide_id"] not in pred_dirs]
    if skipped:
        print(f"no --pred for {skipped}: not scored")

    preds, slides = {}, {}
    for row in rows:
        sid = row["slide_id"]
        if sid not in pred_dirs:
            continue
        preds[sid] = load_prediction(Path(pred_dirs[sid]), args.overrides)
        slides[sid] = score_slide(row, preds[sid], args, roi_over.get(sid),
                                  keep_arrays=args.save_crops)
    vocab = {tuple(p["spec"].names) for p in preds.values()}
    if len(vocab) != 1:
        raise SystemExit(f"predictions use different class vocabularies and cannot be pooled: "
                         f"{sorted(vocab)}")
    class_names = list(vocab.pop())

    records = [r for s in slides.values() for r in s["records"]]
    tiles = [t for s in slides.values() for t in s["tiles"].values()]
    strata = [t["slide"] for t in tiles]
    tkeys = [(t["slide"], t["rect"], t["x0"], t["y0"]) for t in tiles]
    if not any(r["status"] != "FP" for r in records):
        raise SystemExit("no annotated objects inside the evaluation rectangles")
    print(f"\nbootstrap: {args.n_boot} replicates over {len(tiles)} tiles...")

    res = {
        "provenance": {
            "git": _git(), "argv": sys.argv[1:] if argv is None else list(argv),
            "manifest": str(args.manifest), "split": args.split, "tile_px": args.tile,
            "n_boot": args.n_boot, "seed": args.seed, "alpha": args.alpha,
            "slides": {sid: {"prediction_dir": str(p["dir"]),
                             "checkpoint": p["summary"].get("checkpoint"),
                             "working_mpp": p["mpp"],
                             "rectangles": [list(r) for r in slides[sid]["rects"]],
                             "decode": p["cfg"].get("decode"),
                             "tta": p["cfg"].get("infer", {}).get("tta")}
                       for sid, p in preds.items()},
        },
        "conventions": CONVENTIONS,
        "caveats": [CI_SCOPE] + [KNOWN_CAVEATS[s] for s in slides if s in KNOWN_CAVEATS],
        "classes": class_names,
        "counts": pooled_counts(tiles),
        "pooled": summarize(tiles, class_names, args, HEADLINE, strata),
    }

    res["per_slide"] = {}
    for sid, s in slides.items():
        st = list(s["tiles"].values())
        res["per_slide"][sid] = {"counts": pooled_counts(st),
                                 "metrics": summarize(st, class_names, args, HEADLINE)}
    between = {m: between_unit_summary([s["metrics"][m]["estimate"]
                                        for s in res["per_slide"].values()], args.alpha)
               for m in ("PQ", "dice_per_gt", "hd95_um_mean")}
    n_s = len(slides)
    between["note"] = (
        f"{n_s} slide(s) scored: between-slide standard error is not estimable; per-slide "
        f"point estimates are shown instead." if n_s < MIN_UNITS_FOR_SE else
        f"Between-slide mean and standard error over {n_s} slides are in benchmark.json.")
    res["between_slide"] = between

    def groups(field, values):
        out = {}
        for v in values:
            st = subset_tiles(tkeys, records, lambda r: r["status"] != "FP" and r[field] == v)
            n = sum(t["tp"] + t["fn"] for t in st)
            if n:
                out[v] = {"n_gt": n, "metrics": summarize(st, None, args, SUBSET, strata)}
        return out

    res["by_class"] = groups("gt_class", class_names[1:])
    sources = sorted({r["source"] for r in records if r["status"] != "FP" and r["source"]})
    res["by_source"] = groups("source", sources) if sources else {}

    integrity = Counter()
    stray_n = stray_sum = 0.0
    for s in slides.values():
        for k in ("n_instances", "n_below_min_area", "n_multi_component"):
            integrity[k] += s["integrity"].get(k, 0)
        stray_n += s["integrity"].get("n_multi_component", 0)
        stray_sum += s["integrity"]["mean_stray_area_frac"] * s["integrity"].get(
            "n_multi_component", 0)
    integ = dict(integrity, mean_stray_area_frac=(stray_sum / stray_n) if stray_n else 0.0)
    res["edge_cases"] = edge_cases(records, tiles, integ, class_names, args)
    if args.stain_drift:
        res["edge_cases"]["stain_drift"] = stain_drift(slides, preds, args)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    trows = tile_rows(tiles, class_names, args.tile)
    write_csv(out / "objects.csv", records, OBJECT_FIELDS)
    write_csv(out / "tiles.csv", trows, TILE_FIELDS)
    srows = []
    for sid, s in res["per_slide"].items():
        row = {"slide": sid, **s["counts"]}
        for m, v in s["metrics"].items():
            row.update({m: v["estimate"], f"{m}_ci_low": v["ci_low"],
                        f"{m}_ci_high": v["ci_high"]})
        srows.append(row)
    write_csv(out / "slides.csv", srows, list(srows[0]))
    with open(out / "benchmark.json", "w") as f:
        json.dump(_clean(res), f, indent=2)
    write_report(out / "failure_report.md", _clean(res), _clean(trows), records, args)
    if args.save_crops:
        save_crops(out / "crops", slides, _clean(trows), args)
    for s in slides.values():
        s["reader"].close()

    c, p = res["counts"], res["pooled"]
    print(f"\n{'=' * 78}")
    print(f"POOLED over {c['n_gt']} GT objects / {c['n_tiles']} tiles  "
          f"TP {c['tp']} FP {c['fp']} FN {c['fn']}")
    for m in ("PQ", "dice_per_gt", "dice_matched", "hd95_um_mean", "merge_rate", "fg_dice_px"):
        print(f"  {m:<14} {_ci(_clean(p[m]))}")
    print(f"written -> {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
