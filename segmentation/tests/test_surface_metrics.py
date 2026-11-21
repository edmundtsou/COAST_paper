"""Surface-distance maths, pinned on shapes whose answer can be worked out by hand."""
import numpy as np
import pytest

from kidney_panoptic.eval.surface_metrics import (
    component_stats, leak_fraction, pair_surface_metrics, solidity, surface,
)


def _square(shape=(80, 120), y=20, x=20, s=30):
    m = np.zeros(shape, bool)
    m[y:y + s, x:x + s] = True
    return m


def test_identical_masks_have_zero_distance():
    a = _square()
    m = pair_surface_metrics(a, a.copy())
    assert m["hd95"] == 0.0 and m["hd"] == 0.0 and m["assd"] == 0.0


@pytest.mark.parametrize("k", [1, 4, 9])
def test_a_shift_of_k_pixels_gives_hd95_of_k(k):
    m = pair_surface_metrics(_square(), _square(x=20 + k))
    assert m["hd95"] == pytest.approx(k)
    assert m["h95_gt_to_pred"] == pytest.approx(m["h95_pred_to_gt"])


def test_spacing_converts_pixels_to_physical_units():
    a, b = _square(), _square(x=26)
    assert pair_surface_metrics(a, b, spacing=0.5)["hd95"] == pytest.approx(3.0)


def test_one_pixel_spur_moves_the_hausdorff_distance_but_not_hd95():
    """Why the 95th percentile is used: a single stray pixel must not set the score."""
    gt, pred = _square(), _square()
    pred[35, 50:70] = True                         # 1 px wide, 20 px long
    m = pair_surface_metrics(gt, pred)
    assert m["hd"] == pytest.approx(20.0)
    assert m["h95_gt_to_pred"] == 0.0, "every annotated contour pixel is still on the prediction"
    assert m["hd95"] < m["hd"]


def test_a_tendril_shows_up_as_over_reach_and_as_leak():
    """The annexation artefact: object outlined correctly, plus a strip down the interstitium."""
    gt, pred = _square(), _square()
    pred[30:40, 50:100] = True                     # 10 px wide, 50 px long
    m = pair_surface_metrics(gt, pred)
    assert m["h95_pred_to_gt"] > 30, "prediction strays far from the annotation"
    assert m["h95_gt_to_pred"] <= 10, "annotation is still almost entirely covered"
    assert m["hd95"] == m["h95_pred_to_gt"]

    # 500 px of tendril, of which the first 5 columns sit inside the 5 px tolerance.
    assert leak_fraction(gt, pred, tolerance_px=5) == pytest.approx(450 / 1400)
    assert leak_fraction(gt, gt.copy(), tolerance_px=5) == 0.0

    iou = (gt & pred).sum() / (gt | pred).sum()
    assert iou > 0.6, "and overlap alone still calls this a comfortable match"


def test_a_hole_is_not_a_contour():
    """A lumen punched out of the prediction must not be measured against the outline."""
    gt, pred = _square(s=40), _square(s=40)
    pred[35:45, 35:45] = False
    m = pair_surface_metrics(gt, pred)
    assert m["hd95"] == 0.0 and m["hd"] == 0.0
    assert not surface(pred)[34:46, 34:46].any()


def test_array_edge_is_not_a_contour():
    """An object cut by the evaluation window has no surface along the cut."""
    m = np.zeros((40, 40), bool)
    m[0:20, 10:30] = True                          # touches the top edge
    s = surface(m)
    assert not s[0, 11:29].any(), "the cut edge must not count as surface"
    assert s[19, 10:30].all() and s[5, 10] and s[5, 29]


def test_undefined_cases_return_nan_not_zero():
    a = _square()
    assert np.isnan(pair_surface_metrics(a, np.zeros_like(a))["hd95"])
    assert np.isnan(pair_surface_metrics(np.ones((8, 8), bool), np.ones((8, 8), bool))["hd95"])
    assert np.isnan(leak_fraction(a, np.zeros_like(a)))
    assert leak_fraction(np.zeros_like(a), a) == 1.0


def test_component_stats_reports_detached_fragments():
    m = _square()
    assert component_stats(m) == {"n_components": 1, "stray_area_frac": 0.0}
    m[70:75, 100:110] = True                       # 50 px fragment under the same id
    cs = component_stats(m)
    assert cs["n_components"] == 2
    assert cs["stray_area_frac"] == pytest.approx(50 / 950)


def test_solidity_drops_for_a_concave_shape():
    assert solidity(_square()) == pytest.approx(1.0)
    ell = _square(s=40)
    ell[20:45, 35:60] = False                      # cut a corner out -> L shape
    assert solidity(ell) < 0.85
