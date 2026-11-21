"""Slide-scale instance matching that keeps the matched pairs.

``instance_metrics`` answers "what is the PQ of this region" and throws the matching away.
Two things make it unusable for a benchmark over a slide-wide prediction:

* It loops ``(lbl == id).sum()`` once per instance. On a 4096 px region that is fine; on a
  slide map with 13 000 instances and several hundred megapixels it does not finish.
* Per-object Dice, Hausdorff distances and any resampling need to know WHICH prediction
  each annotated object was matched to.

Everything here is a single pass: areas from one ``bincount``, overlaps from one
``np.unique`` over the paired labels, so the cost is linear in pixels and independent of the
number of instances.

The definitions are the ones in ``instance_metrics`` and must stay identical —
``tests/test_matching.py`` pins TP / FP / FN / SQ and the split and merge counts against
``panoptic_quality`` and ``split_merge_rates`` on random label maps.

Matching needs no assignment solver. Two predictions cannot both overlap one object at
IoU > 0.5 (nor two objects one prediction), so above 0.5 the match is unique and reading it
off the overlap list IS the Hungarian solution. That argument fails at or below 0.5, which
is why a lower threshold is refused rather than silently approximated.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Matching:
    """Overlap structure between a ground-truth and a predicted instance map.

    ``pair_*`` arrays list every (gt, pred) pair sharing at least one pixel, as indices into
    ``gt_ids`` / ``pred_ids``. ``match_of_gt`` / ``match_of_pred`` hold the index of the
    matched partner, or -1.
    """
    gt_ids: np.ndarray
    pred_ids: np.ndarray
    gt_area: np.ndarray
    pred_area: np.ndarray
    pair_gt: np.ndarray
    pair_pred: np.ndarray
    pair_inter: np.ndarray
    pair_iou: np.ndarray
    match_of_gt: np.ndarray
    match_of_pred: np.ndarray
    match_iou_of_gt: np.ndarray
    best_of_gt: np.ndarray          # highest-IoU prediction regardless of threshold, or -1
    best_iou_of_gt: np.ndarray
    gt_split: np.ndarray
    gt_merged: np.ndarray
    pred_merging: np.ndarray
    pred_on_gt_frac: np.ndarray     # share of each prediction's area lying on ANY gt object

    @property
    def tp(self) -> int:
        return int((self.match_of_gt >= 0).sum())

    @property
    def fn(self) -> int:
        return int(len(self.gt_ids) - self.tp)

    @property
    def fp(self) -> int:
        return int(len(self.pred_ids) - self.tp)

    @property
    def sum_iou(self) -> float:
        return float(self.match_iou_of_gt[self.match_of_gt >= 0].sum())


def label_areas(lbl: np.ndarray) -> np.ndarray:
    """Pixel count per label value; index 0 is background."""
    return np.bincount(lbl.ravel())


def pq_from_counts(tp: float, fp: float, fn: float, sum_iou: float) -> dict:
    """PQ / SQ / DQ from pooled counts — the form in which they are summed across regions."""
    if tp + fp + fn == 0:
        return {"PQ": 1.0, "SQ": 1.0, "DQ": 1.0}
    sq = sum_iou / tp if tp else 0.0
    dq = tp / (tp + 0.5 * fp + 0.5 * fn)
    return {"PQ": sq * dq, "SQ": sq, "DQ": dq}


def match_instances(gt: np.ndarray, pred: np.ndarray, *, iou_threshold: float = 0.5,
                    overlap_frac: float = 0.20) -> Matching:
    """Match two instance-id maps (0 = background) and flag splits and merges.

    A pair is matched when IoU > ``iou_threshold`` (strict, as in ``panoptic_quality``).
    A GT object is SPLIT when >= 2 predictions each cover ``overlap_frac`` of it, and MERGED
    when a prediction covering ``overlap_frac`` of it does the same to another GT object.
    """
    if iou_threshold < 0.5:
        raise ValueError(
            f"iou_threshold {iou_threshold} < 0.5: matches are no longer unique, so they "
            "cannot be read off the overlaps. Use instance_metrics.f1_at_iou for that.")
    if gt.shape != pred.shape:
        raise ValueError(f"shape mismatch: gt {gt.shape} vs pred {pred.shape}")

    g_area_all, p_area_all = label_areas(gt), label_areas(pred)
    gt_ids = np.flatnonzero(g_area_all[1:]) + 1
    pred_ids = np.flatnonzero(p_area_all[1:]) + 1
    ga, pa = g_area_all[gt_ids], p_area_all[pred_ids]
    G, P = len(gt_ids), len(pred_ids)

    both = (gt > 0) & (pred > 0)
    stride = int(p_area_all.size)
    key, inter = np.unique(gt[both].astype(np.int64) * stride + pred[both],
                           return_counts=True)
    g_pos = np.zeros(g_area_all.size, np.int64)
    g_pos[gt_ids] = np.arange(G)
    p_pos = np.zeros(p_area_all.size, np.int64)
    p_pos[pred_ids] = np.arange(P)
    pg, pp = g_pos[key // stride], p_pos[key % stride]
    iou = inter / (ga[pg] + pa[pp] - inter)

    match_of_gt = np.full(G, -1, np.int64)
    match_of_pred = np.full(P, -1, np.int64)
    match_iou = np.zeros(G)
    hit = iou > iou_threshold
    match_of_gt[pg[hit]] = pp[hit]
    match_of_pred[pp[hit]] = pg[hit]
    match_iou[pg[hit]] = iou[hit]

    best_of_gt = np.full(G, -1, np.int64)
    best_iou = np.zeros(G)
    if len(pg):
        order = np.lexsort((iou, pg))               # by gt, then IoU ascending
        last = np.r_[pg[order][1:] != pg[order][:-1], True]
        best_of_gt[pg[order][last]] = pp[order][last]
        best_iou[pg[order][last]] = iou[order][last]

    covers = (inter / ga[pg]) >= overlap_frac
    gt_split = np.bincount(pg[covers], minlength=G) >= 2
    pred_merging = np.bincount(pp[covers], minlength=P) >= 2
    gt_merged = np.zeros(G, bool)
    gt_merged[pg[covers & pred_merging[pp]]] = True

    on_gt = np.bincount(pp, weights=inter, minlength=P) / np.maximum(pa, 1)

    return Matching(gt_ids, pred_ids, ga, pa, pg, pp, inter, iou, match_of_gt,
                    match_of_pred, match_iou, best_of_gt, best_iou, gt_split, gt_merged,
                    pred_merging, on_gt)


def filter_by_valid(pred: np.ndarray, valid: np.ndarray,
                    min_valid_frac: float = 0.5) -> np.ndarray:
    """``instance_metrics.filter_by_valid`` without the per-instance loop.

    Drops predictions lying mostly in the ignored region; predictions on TRUSTED background
    stay and are scored as false positives.
    """
    area = label_areas(pred)
    inside = np.bincount(pred[valid.astype(bool)], minlength=area.size)
    keep = inside / np.maximum(area, 1) >= min_valid_frac
    keep[0] = False
    return np.where(keep[pred], pred, 0).astype(pred.dtype)
