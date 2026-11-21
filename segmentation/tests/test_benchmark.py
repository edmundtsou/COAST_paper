"""Benchmark scoring core, and the script end to end on a synthetic slide.

The synthetic slide is built so that every accounting rule the benchmark depends on has
exactly one object exercising it, with a count that can be read off the layout.
"""
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import box

from kidney_panoptic.data.rasterize import rasterize_instances
from kidney_panoptic.eval.benchmark import (
    make_pooler, prediction_integrity, score_rect, tile_confusions, tile_statistics,
)
from kidney_panoptic.eval.ground_truth import SlideAnnotations, rasterize_rect

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

NAMES = ["background", "tubule_proximal", "tubule_distal", "tubule_collecting", "glomerulus"]


def _scene():
    """GT: A matched exactly, B matched with a tendril, C missed, D+E merged by one prediction."""
    gt = np.zeros((200, 400), np.int32)
    gt[20:60, 20:60] = 1          # A
    gt[20:60, 100:140] = 2        # B
    gt[100:140, 20:60] = 3        # C
    gt[100:140, 100:140] = 4      # D
    gt[100:140, 142:182] = 5      # E
    pred = np.zeros_like(gt)
    pred[20:60, 20:60] = 11
    pred[20:60, 100:140] = 12
    pred[35:45, 140:180] = 12     # tendril off B
    pred[100:140, 100:182] = 13   # swallows D and E
    pred[150:190, 300:340] = 14   # on trusted background -> false positive
    pred[20:60, 300:340] = 15     # in the ignored region -> not scored
    valid = np.ones(gt.shape, bool)
    valid[0:80, 280:360] = False
    return gt, pred, valid


def _score(**kw):
    gt, pred, valid = _scene()
    return score_rect(gt, pred, valid, gt_class={i: 1 for i in range(1, 6)},
                      pred_class={i: 1 for i in range(11, 16)}, class_names=NAMES, mpp=0.5,
                      **kw)


def test_every_object_gets_one_record_with_the_right_outcome():
    recs = _score()
    by_gt = {r["gt_id"]: r for r in recs if r["gt_id"]}
    assert {g: r["status"] for g, r in by_gt.items()} == {
        1: "TP", 2: "TP", 3: "FN", 4: "FN", 5: "FN"}
    fps = [r for r in recs if r["status"] == "FP"]
    assert sorted(r["pred_id"] for r in fps) == [13, 14]
    assert 15 not in {r["pred_id"] for r in recs}, "ignored-region prediction must be dropped"


def test_failure_types_name_the_mechanism_not_just_the_outcome():
    by_gt = {r["gt_id"]: r["failure"] for r in _score() if r["gt_id"]}
    assert by_gt == {1: "ok", 2: "leak", 3: "miss", 4: "merge", 5: "merge"}
    by_pred = {r["pred_id"]: r["failure"] for r in _score() if r["status"] == "FP"}
    assert by_pred == {13: "fp_on_object", 14: "fp_on_background"}


def test_tendril_is_charged_by_hd95_while_dice_stays_high():
    b = next(r for r in _score() if r["gt_id"] == 2)
    assert b["dice"] > 0.85
    assert b["h95_pred_to_gt_px"] > 25 and b["h95_gt_to_pred_px"] <= 10
    assert b["hd95_um"] == pytest.approx(b["hd95_px"] * 0.5)
    assert b["leak_frac"] == pytest.approx(350 / 2000)
    assert b["pred_solidity"] < 0.85 <= b["gt_solidity"]


def test_coordinates_are_slide_coordinates():
    a = next(r for r in _score(origin_xy=(1000, 5000)) if r["gt_id"] == 1)
    assert (a["cx"], a["cy"]) == pytest.approx((1039.5, 5039.5))


def test_pooled_metrics_zero_fill_missed_objects_and_pool_counts():
    stat = make_pooler([tile_statistics(_score())])
    s = stat(np.array([0]))
    b_iou = 1600 / 2000
    assert s["recall"] == pytest.approx(2 / 5)
    assert s["iou_matched"] == pytest.approx((1 + b_iou) / 2)
    assert s["iou_per_gt"] == pytest.approx((1 + b_iou) / 5), "three misses count as zero"
    assert s["DQ"] == pytest.approx(2 / (2 + 0.5 * 2 + 0.5 * 3))
    assert s["merge_rate"] == pytest.approx(2 / 5)
    # Pooling two copies of the tile must leave every rate unchanged.
    twice = make_pooler([tile_statistics(_score())] * 2)(np.array([0, 1]))
    assert twice["PQ"] == pytest.approx(s["PQ"])


def test_tile_confusion_counts_only_valid_pixels():
    gt, pred, valid = _scene()
    conf = tile_confusions((gt > 0).astype(int), (pred > 0).astype(int), valid, 2, tile=200)
    total = sum(c.sum() for c in conf.values())
    assert total == valid.sum()
    assert set(conf) == {(0, 0), (1, 0)}
    assert conf[(1, 0)][0, 1] == 1600, "the background false positive, and not the ignored one"


def test_prediction_integrity_flags_small_and_fragmented_instances():
    pred = np.zeros((100, 100), np.int32)
    pred[10:40, 10:40] = 1                      # 900 px, fine
    pred[60:70, 10:20] = 2                      # 100 px, under the floor
    pred[60:90, 50:80] = 3
    pred[10:14, 80:84] = 3                      # detached fragment of 3
    pred[0:5, 0:5] = 4                          # cut by the edge -> not judged
    r = prediction_integrity(pred, {1: 1, 2: 1, 3: 1, 4: 1}, NAMES,
                             {"default": 50, "tubule_proximal": 500})
    assert r["n_instances"] == 3
    assert r["n_below_min_area"] == 1 and r["n_multi_component"] == 1


def test_rect_rasterizer_matches_the_patch_rasterizer(spec):
    polys = [box(30.3, 40.7, 90.2, 120.5), box(60, 100, 150, 180), box(-20, 10, 25, 60),
             box(170.5, 20.5, 260, 90)]
    names = ["Tubules", "Tubules2", "Glomeruli", "Tubules3"]
    ann = SlideAnnotations(polys=polys, names=names, sources=["hand"] * 4)
    rect = (10, 5, 210, 165)                    # cuts the third and fourth polygon
    mine, gt_class, meta = rasterize_rect(ann, spec, rect)
    ref, ref_names = rasterize_instances(polys, names, 160, 200, offset_xy=(10, 5))
    assert np.array_equal(mine, ref)
    assert {i: meta[i]["raw_label"] for i in meta} == ref_names
    assert gt_class == {i: spec.canonical_index(n) for i, n in ref_names.items()}


# ------------------------------------------------------------- script, end to end
def _feature(x0, y0, x1, y1, name, source="hand"):
    ring = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {"objectType": "annotation", "classification": {"name": name},
                           "source": source}}


@pytest.fixture
def synthetic_run(tmp_path):
    """A 600 x 800 slide: tissue on the left 520 columns, glass on the right."""
    from conftest import CFG

    H, W = 600, 800
    rgb = np.full((H, W, 3), 240, np.uint8)
    rgb[:, :520] = (205, 120, 170)
    cv2.imwrite(str(tmp_path / "slide.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))

    objects = {  # name -> (x0, y0, x1, y1, raw label, source)
        "A": (40, 40, 110, 110, "Tubules", "hand"),
        "B": (160, 40, 230, 110, "Tubules2", "hand"),
        "C": (40, 200, 110, 270, "Tubules", "curated"),
        "D": (160, 200, 230, 270, "Tubules3", "curated"),
        "E": (300, 300, 380, 380, "Glomeruli", "curated"),
        "F": (40, 400, 110, 470, "Tubules", "curated"),
    }
    feats = [_feature(*v[:4], v[4], v[5]) for v in objects.values()]
    feats.append(_feature(400, 40, 470, 110, "Vessel"))            # ignored class
    (tmp_path / "gt.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": feats}))

    pred = np.zeros((H, W), np.int32)
    pred[40:110, 40:110] = 1                   # A exact
    pred[40:110, 164:234] = 2                  # B shifted 4 px
    pred[200:270, 40:110] = 3                  # C exact ...
    pred[230:240, 110:150] = 3                 # ... plus a tendril
    pred[300:380, 300:380] = 4                 # E exact, wrong class below
    pred[400:470, 40:72] = 5                   # F split in two
    pred[400:470, 76:110] = 6
    pred[250:320, 600:670] = 7                 # on glass -> false positive
    pred[480:550, 300:370] = 8                 # unannotated tissue -> ignored
    cls = {1: 1, 2: 2, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1}       # D missed entirely
    out = tmp_path / "pred"
    out.mkdir()
    np.savez_compressed(out / "instance_map.npz", instance_map=pred,
                        class_of_id=np.array(sorted(cls.items()), np.int64),
                        score_of_id=np.array([[i, 0.9] for i in cls], np.float64))
    cfg = dict(CFG, patch={"annotations_space": "level"}, wsi={"level": 0, "manual_mpp": 0.5},
               annotation={"dilate_px_inner": 5, "dilate_px": 30},
               ignore_strategy="dilated_gt_two_radius_plus_tissue",
               tissue={"min_object_px": 0, "fill_holes_px": 0, "dilate_px": 0},
               decode={"min_area": {"default": 100}}, infer={"tta": "none"})
    (out / "summary.json").write_text(json.dumps({
        "slide": str(tmp_path / "slide.png"), "checkpoint": "synthetic.pt", "level": 0,
        "working_mpp": 0.5, "scale_to_full": 1, "slide_size_work": [W, H],
        "region": [0, 0, W, H], "config": cfg}))
    (tmp_path / "manifest.csv").write_text(
        "slide_id,image_path,geojson_path,stain,species,split,level,manual_mpp,roi\n"
        f"S1,{tmp_path / 'slide.png'},{tmp_path / 'gt.geojson'},H&E,mouse,val,0,0.5,"
        f'"0,0,{W},{H}"\n')

    import benchmark_segmentation as bench

    res_dir = tmp_path / "bench"
    bench.main(["--manifest", str(tmp_path / "manifest.csv"), "--pred", f"S1={out}",
                "--out-dir", str(res_dir), "--tile", "256", "--n-boot", "40",
                "--min-tile-objects", "1", "--worst-k", "5", "--save-crops"])
    return res_dir


def test_script_accounts_for_every_object_on_a_synthetic_slide(synthetic_run):
    with open(synthetic_run / "objects.csv") as f:
        rows = list(csv.DictReader(f))
    assert sum(r["status"] != "FP" for r in rows) == 6, \
        "six annotated objects; the Vessel is an ignored class"
    status = {}
    for r in rows:
        status[r["status"]] = status.get(r["status"], 0) + 1
    # TP: A, B, C, E.  FN: D (missed), F (split).  FP: the two halves of F and the one on glass.
    assert status == {"TP": 4, "FN": 2, "FP": 3}

    res = json.loads((synthetic_run / "benchmark.json").read_text())
    c = res["counts"]
    assert (c["tp"], c["fp"], c["fn"], c["n_gt"]) == (4, 3, 2, 6)
    assert res["pooled"]["DQ"]["estimate"] == pytest.approx(4 / (4 + 1.5 + 1.0))
    assert res["pooled"]["split_rate"]["estimate"] == pytest.approx(1 / 6)

    fail = {r["failure"] for r in rows}
    assert {"split", "miss", "leak", "fp_on_object", "fp_on_background"} <= fail
    shifted = next(r for r in rows if r["gt_class"] == "tubule_distal")
    assert float(shifted["hd95_px"]) == pytest.approx(4.0)
    assert float(shifted["hd95_um"]) == pytest.approx(2.0)


def test_script_reports_intervals_breakdowns_and_caveats(synthetic_run):
    res = json.loads((synthetic_run / "benchmark.json").read_text())
    pq = res["pooled"]["PQ"]
    assert pq["ci_low"] <= pq["estimate"] <= pq["ci_high"]
    assert res["pooled"]["dice_per_gt"]["estimate"] < res["pooled"]["dice_matched"]["estimate"]
    assert set(res["by_source"]) == {"hand", "curated"}
    assert res["by_source"]["hand"]["metrics"]["recall"]["estimate"] == 1.0
    assert "tubule_proximal" in res["by_class"] and "glomerulus" in res["by_class"]
    assert res["between_slide"]["PQ"]["se"] is None, "one slide has no between-slide SE"
    assert any("not estimable" in c for c in res["caveats"])

    ec = res["edge_cases"]
    assert ec["class_agreement_among_matched"]["accuracy"] == pytest.approx(3 / 4)
    assert ec["small_and_disconnected"]["false_positives"]["on_background"] == 1
    assert ec["small_and_disconnected"]["all_predictions_in_rectangles"]["n_below_min_area"] == 0
    assert ec["boundary_leakage"]["pred_px_on_trusted_background_frac"] > 0

    report = (synthetic_run / "failure_report.md").read_text()
    for heading in ("Worst tiles by Dice", "Worst tiles by HD95", "Failure types",
                    "Boundary leakage", "Small and disconnected"):
        assert heading in report, heading
    assert list((synthetic_run / "crops").glob("*.png"))
    with open(synthetic_run / "tiles.csv") as f:
        tiles = list(csv.DictReader(f))
    assert sum(int(t["n_gt"]) for t in tiles) == 6


def test_stain_scaling_is_near_identity_at_one_and_darkens_above_it():
    import benchmark_segmentation as bench

    rgb = np.full((8, 8, 3), (205, 120, 170), np.uint8)
    same = bench.scale_stain(rgb, 1.0, 1.0)
    assert np.abs(same.astype(int) - rgb).max() <= 2, "round trip is near-identity"
    darker, lighter = bench.scale_stain(rgb, 1.3, 1.3), bench.scale_stain(rgb, 0.7, 0.7)
    assert darker.mean() < rgb.mean() < lighter.mean()


def test_drift_windows_stay_inside_a_rectangle_and_prefer_dense_areas():
    import benchmark_segmentation as bench

    recs = [{"status": "TP", "cx": 150 + 10 * i, "cy": 150.0} for i in range(8)]
    recs += [{"status": "FN", "cx": 900.0, "cy": 900.0}]
    wins = bench.pick_windows([(0, 0, 1000, 1000)], recs, size=400, n=2)
    assert len(wins) == 2
    assert all(0 <= x0 and x1 <= 1000 and 0 <= y0 and y1 <= 1000 for x0, y0, x1, y1 in wins)
    x0, y0, x1, y1 = wins[0]
    assert x0 <= 150 and x1 >= 220, "the dense cluster is picked first"
