"""Contour-distance metrics for one object pair: HD95, ASSD, leak fraction.

Overlap scores are area-weighted, so a thin error that covers few pixels barely moves them
however far it reaches. The interstitium-annexation artefact is exactly that shape — a
tendril down the interstitium, or a neighbour's wall annexed — and it left mean IoU at 0.883
while 37.7 % of predicted tubules carried it. Surface distances are the metrics that see it.

Conventions, stated because the literature is not uniform:

* The SURFACE of a mask is its OUTER contour: holes are filled first, then mask pixels with
  a 4-neighbour outside it are taken. Annotations are outlines — QuPath polygons carry no
  holes — while a predicted mask can have a lumen or another instance punched out of it,
  and an annotation can have a smaller annotation painted inside it. Counting those inner
  edges as contour measures the distance from a lumen to the object's outline, which is the
  object's radius and not an error: on the human cohort it gave glomeruli with Dice 0.99 an
  HD95 of 45 µm. Overlap metrics are NOT hole-filled; a hole still costs IoU.
* A pixel on the edge of the array is not a surface pixel. The array edge is where the
  evaluation window cut the object, not a contour anyone drew or predicted, so callers must
  crop with a margin everywhere EXCEPT at a genuine window edge.
* HD95 is ``max`` of the two directed 95th percentiles (MONAI, DeepMind ``surface-distance``).
  MedPy instead pools both directed sets and takes one percentile; the two differ whenever
  the contours have unequal length, and the pooled form lets a long clean contour dilute a
  short bad one.
* Percentiles use numpy's default linear interpolation.

The two directed terms are returned separately because their difference is diagnostic:
prediction-to-ground-truth is how far the prediction strays from the annotation (over-reach,
leakage), ground-truth-to-prediction is how much annotated contour the prediction never
reached.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from scipy import ndimage as ndi

_CROSS = ndi.generate_binary_structure(2, 1)
_FULL = ndi.generate_binary_structure(2, 2)


def surface(mask: np.ndarray) -> np.ndarray:
    """Outer contour of ``mask`` (holes filled); pixels on the array edge are never surface."""
    mask = ndi.binary_fill_holes(mask.astype(bool))
    return mask & ~ndi.binary_erosion(mask, _CROSS, border_value=1)


def surface_distances(gt: np.ndarray, pred: np.ndarray,
                      spacing: float = 1.0) -> Optional[tuple[np.ndarray, np.ndarray]]:
    """Directed surface distances ``(gt -> pred, pred -> gt)``, or None if a surface is empty."""
    sg, sp = surface(gt), surface(pred)
    if not sg.any() or not sp.any():
        return None
    to_pred = ndi.distance_transform_edt(~sp, sampling=spacing)
    to_gt = ndi.distance_transform_edt(~sg, sampling=spacing)
    return to_pred[sg], to_gt[sp]


def pair_surface_metrics(gt: np.ndarray, pred: np.ndarray, spacing: float = 1.0) -> dict:
    """HD95, both directed terms, the plain Hausdorff distance and ASSD for one pair.

    Every value is NaN when either mask has no surface, which happens only for an empty mask
    or one whose whole outline lies on the window edge.
    """
    d = surface_distances(gt, pred, spacing)
    if d is None:
        nan = float("nan")
        return {"hd95": nan, "h95_gt_to_pred": nan, "h95_pred_to_gt": nan, "hd": nan,
                "assd": nan}
    d_gp, d_pg = d
    a, b = float(np.percentile(d_gp, 95)), float(np.percentile(d_pg, 95))
    return {
        "hd95": max(a, b),
        "h95_gt_to_pred": a,
        "h95_pred_to_gt": b,
        "hd": float(max(d_gp.max(), d_pg.max())),
        "assd": float((d_gp.sum() + d_pg.sum()) / (d_gp.size + d_pg.size)),
    }


def leak_fraction(gt: np.ndarray, pred: np.ndarray, tolerance_px: float = 5.0) -> float:
    """Share of the prediction lying more than ``tolerance_px`` outside the annotation.

    The tolerance is the width of the trusted-background ring (ADR 0003): inside it a
    disagreement is ordinary contour jitter, beyond it the prediction is on pixels the
    annotator positively marked as not this object.
    """
    pred = pred.astype(bool)
    n = int(pred.sum())
    if n == 0:
        return float("nan")
    gt = gt.astype(bool)
    if not gt.any():
        return 1.0
    return float((ndi.distance_transform_edt(~gt)[pred] > tolerance_px).sum() / n)


def component_stats(mask: np.ndarray) -> dict:
    """Connected components (8-connectivity) of one instance mask.

    One instance id should be one piece. More than one means stitching or the area filter
    left a detached fragment under the same id, which inflates area and breaks any shape
    measurement taken from it.
    """
    lab, n = ndi.label(mask.astype(bool), _FULL)
    if n == 0:
        return {"n_components": 0, "stray_area_frac": 0.0}
    sizes = np.bincount(lab.ravel())[1:]
    return {"n_components": int(n),
            "stray_area_frac": float(1.0 - sizes.max() / sizes.sum())}


def solidity(mask: np.ndarray) -> float:
    """Area over convex-hull area — the shape statistic the annexation artefact lowers."""
    from skimage.measure import regionprops

    props = regionprops(mask.astype(np.uint8))
    return float(props[0].solidity) if props else float("nan")
