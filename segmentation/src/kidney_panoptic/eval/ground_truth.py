"""Ground truth for an arbitrary slide rectangle: instance map, classes, valid mask.

``eval_regions.py`` and ``extract_patches.py`` each carry their own copy of "load the
GeoJSON, sort polygons by role, scale them, rasterize, build the valid mask". This is that
logic once, for callers that score a rectangle of a slide rather than a fixed-size patch.

The rasterizer paints each polygon into its own bounding box instead of into a canvas the
size of the whole rectangle. ``rasterize_instances`` does the latter, which costs one full
canvas per polygon and is what makes it slow on a rectangle spanning most of a slide. The
painting rule is unchanged — largest first, so a smaller object wins the pixels it shares
with a larger one — and ``tests/test_benchmark.py`` pins the two against each other.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from shapely.affinity import scale as shapely_scale
from shapely.affinity import translate
from shapely.geometry import Polygon, box

from ..data.classes import ClassSpec
from ..data.geojson_io import load_geojson_instances
from ..data.ignore import build_valid_mask
from ..data.rasterize import _rasterize_one

Rect = tuple[int, int, int, int]            # x0, y0, x1, y1 in working pixels


@dataclass
class SlideAnnotations:
    """One slide's annotations in working-resolution pixels, sorted by role."""
    polys: list[Polygon] = field(default_factory=list)
    names: list[str] = field(default_factory=list)        # RAW annotation label
    sources: list[str] = field(default_factory=list)      # `source` property, or ""
    bg_polys: list[Polygon] = field(default_factory=list)
    roi_polys: list[Polygon] = field(default_factory=list)


def load_slide_annotations(geojson_path: str | Path, spec: ClassSpec,
                           to_work: float = 1.0) -> SlideAnnotations:
    """Read a QuPath GeoJSON and split it into instances / background / dense ROIs.

    ``to_work`` scales annotation coordinates into working pixels; it is 1.0 when the
    annotations were drawn on the working-level image (``patch.annotations_space: level``).
    """
    ann = SlideAnnotations()
    for inst in load_geojson_instances(geojson_path):
        role = spec.role(inst.class_name)
        if role == "ignore":
            continue
        g = inst.polygon if to_work == 1.0 else shapely_scale(
            inst.polygon, xfact=to_work, yfact=to_work, origin=(0, 0))
        if role == "instance":
            ann.polys.append(g)
            ann.names.append(inst.class_name)
            ann.sources.append(str((inst.raw_properties or {}).get("source", "")))
        elif role == "background":
            ann.bg_polys.append(g)
        else:
            ann.roi_polys.append(g)
    return ann


def annotation_bounds(ann: SlideAnnotations, width: int, height: int, pad: int = 64) -> Rect:
    """Bounding rectangle of every instance polygon, padded and clipped to the slide."""
    if not ann.polys:
        raise ValueError("no instance annotations: cannot derive an evaluation rectangle")
    b = np.array([p.bounds for p in ann.polys])
    return (max(0, int(np.floor(b[:, 0].min())) - pad),
            max(0, int(np.floor(b[:, 1].min())) - pad),
            min(width, int(np.ceil(b[:, 2].max())) + pad),
            min(height, int(np.ceil(b[:, 3].max())) + pad))


def _paint(polys: list[Polygon], rect: Rect) -> tuple[np.ndarray, list[int]]:
    """Paint polygons into ``rect``, largest first. Returns the id map and, for each id
    (1-based), the index of its polygon in ``polys``."""
    x0, y0, x1, y1 = rect
    id_map = np.zeros((y1 - y0, x1 - x0), np.int32)
    window = box(x0, y0, x1, y1)
    owner: list[int] = []
    for idx in sorted(range(len(polys)), key=lambda i: polys[i].area, reverse=True):
        poly = polys[idx]
        if poly.is_empty or not poly.intersects(window):
            continue
        bx0, by0, bx1, by1 = poly.bounds
        ax0, ay0 = max(x0, int(np.floor(bx0))), max(y0, int(np.floor(by0)))
        ax1, ay1 = min(x1, int(np.ceil(bx1)) + 1), min(y1, int(np.ceil(by1)) + 1)
        if ax1 <= ax0 or ay1 <= ay0:
            continue
        mask = _rasterize_one(translate(poly, xoff=-ax0, yoff=-ay0), ay1 - ay0, ax1 - ax0)
        if not mask.any():
            continue
        owner.append(idx)
        id_map[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0][mask] = len(owner)
    return id_map, owner


def rasterize_rect(ann: SlideAnnotations, spec: ClassSpec,
                   rect: Rect) -> tuple[np.ndarray, dict[int, int], dict[int, dict]]:
    """Instance map for ``rect`` plus, per id, its class index and its annotation metadata.

    Objects crossing the rectangle's edge are kept and clipped, as in ``eval_regions.py``.
    """
    id_map, owner = _paint(ann.polys, rect)
    gt_class = {i + 1: spec.canonical_index(ann.names[k]) for i, k in enumerate(owner)}
    meta = {i + 1: {"raw_label": ann.names[k], "source": ann.sources[k]}
            for i, k in enumerate(owner)}
    return id_map, gt_class, meta


def poly_mask(polys: list[Polygon], rect: Rect) -> np.ndarray:
    return _paint(polys, rect)[0] > 0


def rect_valid_mask(gt: np.ndarray, tissue: np.ndarray, ann: SlideAnnotations, rect: Rect,
                    cfg: dict) -> np.ndarray:
    """The three-way ignore mask (ADR 0003) for ``rect``, with the strategy and ring widths
    the model was trained under."""
    acfg = cfg.get("annotation", {}) or {}
    return build_valid_mask(
        gt, strategy=cfg.get("ignore_strategy", "dilated_gt_two_radius_plus_tissue"),
        tissue_mask=tissue,
        background_mask=poly_mask(ann.bg_polys, rect),
        dense_roi_mask=poly_mask(ann.roi_polys, rect),
        dilate_px_inner=int(acfg.get("dilate_px_inner", 5)),
        dilate_px=int(acfg.get("dilate_px", 30)),
    )
