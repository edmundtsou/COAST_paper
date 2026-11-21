"""Per-object scoring and tile-pooled summaries for the publication benchmark.

``score_rect`` turns one evaluation rectangle into a list of per-object RECORDS — one per
annotated object and one per unmatched prediction. Everything else (slide summaries,
confidence intervals, the failure report) is computed from those records and from per-tile
pixel confusion matrices, so nothing has to be re-inferred to ask a new question.

Three conventions decide what the numbers mean:

* **Matching is class-agnostic** (ADR 0004): a correctly outlined tubule is a true positive
  whichever segment it was called. Class agreement is reported separately.
* **Dice and IoU are reported two ways.** The matched-only mean is conditioned on
  IoU > 0.5 and therefore cannot fall below Dice 0.667 however many objects are missed. The
  per-ground-truth mean counts every missed object as 0 and is the one that reflects what a
  reader would call accuracy.
* **Surface distances exist only for matched pairs.** A missed object has no predicted
  contour to measure to, and inventing a penalty distance would put an arbitrary constant
  into the mean. HD95 is always printed next to the detection counts for that reason.
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np
from scipy import ndimage as ndi

from .matching import filter_by_valid, label_areas, match_instances, pq_from_counts
from .surface_metrics import component_stats, leak_fraction, pair_surface_metrics, solidity

# A matched prediction is flagged as LEAKING when more than this share of its area lies
# beyond the trusted ring around the annotation. Solidity < 0.85 is the shape criterion the
# annexation artefact was characterised with (1.5 % of hand annotations fall below it).
LEAK_FRAC_FLAG = 0.05
SOLIDITY_FLAG = 0.85

_NAN = float("nan")


def _slices(lbl: np.ndarray) -> dict[int, tuple[slice, slice]]:
    return {i + 1: s for i, s in enumerate(ndi.find_objects(lbl)) if s is not None}


def _union(a, b, shape, pad: int = 1):
    """Bounding box of two slices, padded but never past the array (window) edge."""
    y0 = max(0, min(a[0].start, b[0].start) - pad)
    x0 = max(0, min(a[1].start, b[1].start) - pad)
    y1 = min(shape[0], max(a[0].stop, b[0].stop) + pad)
    x1 = min(shape[1], max(a[1].stop, b[1].stop) + pad)
    return slice(y0, y1), slice(x0, x1)


def _centroid(mask: np.ndarray, sl) -> tuple[float, float]:
    ys, xs = np.nonzero(mask)
    return float(xs.mean() + sl[1].start), float(ys.mean() + sl[0].start)


def _border_ids(lbl: np.ndarray) -> set[int]:
    edge = np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]])
    return set(int(i) for i in np.unique(edge) if i != 0)


def score_rect(
    gt: np.ndarray,
    pred: np.ndarray,
    valid: np.ndarray,
    *,
    gt_class: dict[int, int],
    pred_class: dict[int, int],
    class_names: list[str],
    mpp: float,
    origin_xy: tuple[int, int] = (0, 0),
    gt_meta: Optional[dict[int, dict]] = None,
    leak_tolerance_px: float = 5.0,
    iou_threshold: float = 0.5,
    overlap_frac: float = 0.20,
    min_valid_frac: float = 0.5,
) -> list[dict]:
    """Score one rectangle and return per-object records.

    ``gt`` and ``pred`` are instance-id maps of the same shape; ``valid`` is the three-way
    ignore mask. Predictions lying mostly in the ignored region are dropped before scoring,
    predictions on trusted background are kept and become false positives. Coordinates in
    the records are slide coordinates (``origin_xy`` added), in working pixels.
    """
    scored = filter_by_valid(pred, valid, min_valid_frac)
    m = match_instances(gt, scored, iou_threshold=iou_threshold, overlap_frac=overlap_frac)
    g_sl, p_sl = _slices(gt), _slices(scored)
    g_border, p_border = _border_ids(gt), _border_ids(scored)
    ox, oy = origin_xy
    gt_meta = gt_meta or {}

    def name(ci):
        return class_names[ci] if ci is not None and 0 <= ci < len(class_names) else ""

    def base():
        return {"status": "", "gt_id": None, "pred_id": None, "gt_class": "",
                "pred_class": "", "raw_label": "", "source": "", "cx": _NAN, "cy": _NAN,
                "gt_area": _NAN, "pred_area": _NAN, "iou": 0.0, "dice": 0.0,
                "best_iou": 0.0, "hd95_px": _NAN, "h95_gt_to_pred_px": _NAN,
                "h95_pred_to_gt_px": _NAN, "hd_px": _NAN, "assd_px": _NAN,
                "hd95_um": _NAN, "assd_um": _NAN, "leak_frac": _NAN, "area_ratio": _NAN,
                "gt_solidity": _NAN, "pred_solidity": _NAN, "n_components": None,
                "stray_area_frac": _NAN, "pred_on_gt_frac": _NAN, "touches_border": False,
                "split": False, "merged": False, "failure": "ok"}

    records: list[dict] = []
    for gi, gid in enumerate(m.gt_ids):
        gid = int(gid)
        r = base()
        sl = g_sl[gid]
        g_own = gt[sl] == gid
        cx, cy = _centroid(g_own, sl)
        r.update(gt_id=gid, gt_class=name(gt_class.get(gid)), cx=cx + ox, cy=cy + oy,
                 gt_area=int(m.gt_area[gi]), gt_solidity=solidity(g_own),
                 best_iou=float(m.best_iou_of_gt[gi]), split=bool(m.gt_split[gi]),
                 merged=bool(m.gt_merged[gi]), touches_border=gid in g_border,
                 **gt_meta.get(gid, {}))
        pj = int(m.match_of_gt[gi])
        if pj < 0:
            r["status"] = "FN"
        else:
            pid = int(m.pred_ids[pj])
            iou = float(m.match_iou_of_gt[gi])
            crop = _union(sl, p_sl[pid], gt.shape)
            g, p = gt[crop] == gid, scored[crop] == pid
            sm = pair_surface_metrics(g, p)
            r.update(status="TP", pred_id=pid, pred_class=name(pred_class.get(pid)),
                     pred_area=int(m.pred_area[pj]), iou=iou, dice=2 * iou / (1 + iou),
                     hd95_px=sm["hd95"], h95_gt_to_pred_px=sm["h95_gt_to_pred"],
                     h95_pred_to_gt_px=sm["h95_pred_to_gt"], hd_px=sm["hd"],
                     assd_px=sm["assd"], hd95_um=sm["hd95"] * mpp, assd_um=sm["assd"] * mpp,
                     leak_frac=leak_fraction(g, p, leak_tolerance_px),
                     area_ratio=float(m.pred_area[pj] / m.gt_area[gi]),
                     pred_solidity=solidity(p), pred_on_gt_frac=float(m.pred_on_gt_frac[pj]),
                     touches_border=gid in g_border or pid in p_border,
                     **component_stats(p))
        r["failure"] = _failure_type(r)
        records.append(r)

    for pj in np.flatnonzero(m.match_of_pred < 0):
        pid = int(m.pred_ids[pj])
        sl = p_sl[pid]
        p = scored[sl] == pid
        cx, cy = _centroid(p, sl)
        r = base()
        on_gt = float(m.pred_on_gt_frac[pj])
        r.update(status="FP", pred_id=pid, pred_class=name(pred_class.get(pid)),
                 cx=cx + ox, cy=cy + oy, pred_area=int(m.pred_area[pj]),
                 pred_solidity=solidity(p), pred_on_gt_frac=on_gt,
                 touches_border=pid in p_border, merged=bool(m.pred_merging[pj]),
                 failure="fp_on_object" if on_gt >= 0.5 else "fp_on_background",
                 **component_stats(p))
        records.append(r)
    return records


def _failure_type(r: dict) -> str:
    """One label per annotated object, most structural cause first.

    A merged object is usually also a false negative; calling it a miss would hide the
    mechanism, so merge and split are tested before the detection outcome.
    """
    if r["merged"]:
        return "merge"
    if r["split"]:
        return "split"
    if r["status"] == "FN":
        return "miss" if r["best_iou"] < 0.10 else "poor_overlap"
    if r["leak_frac"] > LEAK_FRAC_FLAG:
        return "leak"
    return "ok"


# ------------------------------------------------------------------ pixel level
def tile_confusions(gt_sem: np.ndarray, pred_sem: np.ndarray, valid: np.ndarray,
                    n_classes: int, tile: int) -> dict[tuple[int, int], np.ndarray]:
    """Per-tile ``(C, C)`` confusion matrix (rows ground truth) over valid pixels.

    Keyed by the tile's (column, row) index in a grid anchored at the array origin. Tiles
    with no valid pixel are omitted.
    """
    out = {}
    h, w = gt_sem.shape
    for ty, y in enumerate(range(0, h, tile)):
        for tx, x in enumerate(range(0, w, tile)):
            v = valid[y:y + tile, x:x + tile]
            if not v.any():
                continue
            g = gt_sem[y:y + tile, x:x + tile][v].astype(np.int64)
            p = pred_sem[y:y + tile, x:x + tile][v].astype(np.int64)
            out[(tx, ty)] = np.bincount(g * n_classes + p, minlength=n_classes ** 2
                                        ).reshape(n_classes, n_classes)
    return out


def class_lut(class_of_id: dict[int, int], max_id: int) -> np.ndarray:
    """Lookup table instance id -> class index (0 for background and unknown ids)."""
    lut = np.zeros(max_id + 1, np.int64)
    for i, c in class_of_id.items():
        if 0 < i <= max_id and c is not None:
            lut[i] = c
    return lut


# ----------------------------------------------------------------- tile pooling
_SCALARS = ("tp", "fp", "fn", "sum_iou", "n_split", "n_merged")
_ARRAYS = ("dice_gt", "iou_gt", "dice_tp", "hd95_um", "hd95_px", "assd_um", "leak_frac")


def tile_statistics(records: list[dict], conf: Optional[np.ndarray] = None) -> dict:
    """Sufficient statistics of one tile: counts, per-object value lists, pixel confusion."""
    gts = [r for r in records if r["status"] in ("TP", "FN")]
    tps = [r for r in gts if r["status"] == "TP"]

    def arr(rows, key):
        v = np.array([r[key] for r in rows], float)
        return v[np.isfinite(v)]

    return {
        "tp": len(tps), "fn": len(gts) - len(tps),
        "fp": sum(r["status"] == "FP" for r in records),
        "sum_iou": float(sum(r["iou"] for r in tps)),
        "n_split": sum(r["split"] for r in gts), "n_merged": sum(r["merged"] for r in gts),
        "dice_gt": arr(gts, "dice"), "iou_gt": arr(gts, "iou"), "dice_tp": arr(tps, "dice"),
        "hd95_um": arr(tps, "hd95_um"), "hd95_px": arr(tps, "hd95_px"),
        "assd_um": arr(tps, "assd_um"), "leak_frac": arr(tps, "leak_frac"),
        "conf": conf,
    }


def make_pooler(tiles: list[dict], class_names: Optional[list[str]] = None
                ) -> Callable[[np.ndarray], dict]:
    """Build ``stat_fn(idx)`` for ``cluster_bootstrap``: pooled metrics over tiles ``idx``.

    Every metric is recomputed from summed counts and concatenated per-object values, never
    averaged over tiles — a tile with one object must not weigh as much as one with thirty.
    """
    scal = np.array([[t[k] for k in _SCALARS] for t in tiles], float).reshape(len(tiles), -1)
    confs = [t["conf"] for t in tiles]
    has_conf = any(c is not None for c in confs)
    if has_conf:
        shape = next(c for c in confs if c is not None).shape
        conf = np.stack([c if c is not None else np.zeros(shape, np.int64) for c in confs])

    def mean(idx, key, fn=np.mean):
        parts = [tiles[i][key] for i in idx if tiles[i][key].size]
        return float(fn(np.concatenate(parts))) if parts else _NAN

    def div(a, b):
        return float(a / b) if b else _NAN

    def stat(idx: np.ndarray) -> dict:
        tp, fp, fn, sum_iou, n_split, n_merged = scal[idx].sum(axis=0) if len(idx) else [0] * 6
        n_gt = tp + fn
        out = dict(pq_from_counts(tp, fp, fn, sum_iou)) if (tp + fp + fn) else \
            {"PQ": _NAN, "SQ": _NAN, "DQ": _NAN}
        out.update({
            "recall": div(tp, n_gt), "precision": div(tp, tp + fp),
            "dice_per_gt": mean(idx, "dice_gt"), "iou_per_gt": mean(idx, "iou_gt"),
            "dice_matched": mean(idx, "dice_tp"), "iou_matched": div(sum_iou, tp),
            "hd95_um_mean": mean(idx, "hd95_um"),
            "hd95_um_median": mean(idx, "hd95_um", np.median),
            "hd95_px_mean": mean(idx, "hd95_px"),
            "assd_um_mean": mean(idx, "assd_um"),
            "leak_frac_mean": mean(idx, "leak_frac"),
            "split_rate": div(n_split, n_gt), "merge_rate": div(n_merged, n_gt),
        })
        if has_conf:
            c = conf[idx].sum(axis=0)
            inter, g_fg, p_fg = c[1:, 1:].sum(), c[1:, :].sum(), c[:, 1:].sum()
            out["fg_dice_px"] = div(2 * inter, g_fg + p_fg)
            out["fg_iou_px"] = div(inter, g_fg + p_fg - inter)
            for ci, cname in enumerate(class_names or []):
                if ci == 0:
                    continue
                g, p = c[ci, :].sum(), c[:, ci].sum()
                out[f"dice_px[{cname}]"] = div(2 * c[ci, ci], g + p)
        return out

    return stat


def pooled_counts(tiles: list[dict]) -> dict:
    tot = {k: int(sum(t[k] for t in tiles)) for k in ("tp", "fp", "fn", "n_split", "n_merged")}
    tot["n_gt"] = tot["tp"] + tot["fn"]
    tot["n_pred"] = tot["tp"] + tot["fp"]
    tot["n_tiles"] = len(tiles)
    return tot


# ------------------------------------------------------- prediction-only checks
def prediction_integrity(pred: np.ndarray, pred_class: dict[int, int],
                         class_names: list[str], min_area: dict) -> dict:
    """Checks on the predicted map alone, over instances not cut by the rectangle edge.

    * instances below their class's ``decode.min_area`` floor — the decode promises none;
    * instance ids made of more than one connected component.
    """
    areas = label_areas(pred)
    border = _border_ids(pred)
    default = float(min_area.get("default", 0))
    n = n_small = n_multi = 0
    stray = []
    for pid, sl in _slices(pred).items():
        if pid in border:
            continue
        n += 1
        ci = pred_class.get(pid)
        cname = class_names[ci] if ci is not None and ci < len(class_names) else ""
        if areas[pid] < float(min_area.get(cname, default)):
            n_small += 1
        cs = component_stats(pred[sl] == pid)
        if cs["n_components"] > 1:
            n_multi += 1
            stray.append(cs["stray_area_frac"])
    return {"n_instances": n, "n_below_min_area": n_small, "n_multi_component": n_multi,
            "multi_component_rate": (n_multi / n) if n else None,
            "mean_stray_area_frac": float(np.mean(stray)) if stray else 0.0}
