"""The slide-scale matcher must be the SAME metric as instance_metrics, only faster.

If these two ever drift apart, the benchmark's PQ stops being comparable with every PQ the
training loop and eval_regions.py have reported — silently, since both would still look
plausible.
"""
import numpy as np
import pytest

from kidney_panoptic.eval import instance_metrics as im
from kidney_panoptic.eval.matching import filter_by_valid, match_instances, pq_from_counts


def _random_blobs(rng, shape=(96, 96), n=14):
    lbl = np.zeros(shape, np.int32)
    for i in range(1, n + 1):
        h, w = rng.integers(6, 28, size=2)
        y, x = rng.integers(0, shape[0] - h), rng.integers(0, shape[1] - w)
        lbl[y:y + h, x:x + w] = i
    return lbl


@pytest.mark.parametrize("seed", range(12))
def test_matcher_reproduces_panoptic_quality_and_split_merge_on_random_maps(seed):
    rng = np.random.default_rng(seed)
    gt, pred = _random_blobs(rng), _random_blobs(rng)
    pred[:40] = np.where(rng.random((40, 96)) < 0.7, gt[:40], pred[:40])   # some real matches

    m = match_instances(gt, pred)
    ref = im.panoptic_quality(gt, pred)
    assert (m.tp, m.fp, m.fn) == (ref["TP"], ref["FP"], ref["FN"])
    mine = pq_from_counts(m.tp, m.fp, m.fn, m.sum_iou)
    for k in ("PQ", "SQ", "DQ"):
        assert mine[k] == pytest.approx(ref[k]), k

    sm = im.split_merge_rates(gt, pred)
    assert int(m.gt_split.sum()) == sm["n_split"]
    assert int(m.gt_merged.sum()) == sm["n_merged_gt"]
    assert int(m.pred_merging.sum()) == sm["n_merging_preds"]


def test_matcher_keeps_the_pairs_and_their_iou():
    gt = np.zeros((40, 80), np.int32)
    gt[10:30, 5:35] = 7                    # non-contiguous ids on purpose
    gt[10:30, 45:75] = 3
    pred = np.zeros_like(gt)
    pred[10:30, 5:30] = 12                 # 25 of 30 columns of object 7 -> IoU 5/6
    m = match_instances(gt, pred)

    by_gt = {int(g): int(m.pred_ids[j]) if j >= 0 else None
             for g, j in zip(m.gt_ids, m.match_of_gt)}
    assert by_gt == {3: None, 7: 12}
    assert m.match_iou_of_gt[list(m.gt_ids).index(7)] == pytest.approx(25 / 30)
    assert m.best_iou_of_gt[list(m.gt_ids).index(3)] == 0.0


def test_half_overlap_is_not_a_match_because_the_threshold_is_strict():
    gt = np.zeros((10, 40), np.int32); gt[:, 0:20] = 1
    pred = np.zeros_like(gt); pred[:, 0:10] = 1         # IoU exactly 0.5
    m = match_instances(gt, pred)
    assert m.tp == 0 and m.best_iou_of_gt[0] == pytest.approx(0.5)


def test_threshold_below_half_is_refused_rather_than_approximated():
    z = np.zeros((4, 4), np.int32)
    with pytest.raises(ValueError, match="no longer unique"):
        match_instances(z, z, iou_threshold=0.3)


def test_empty_maps_do_not_crash_and_score_as_perfect():
    z = np.zeros((16, 16), np.int32)
    m = match_instances(z, z)
    assert (m.tp, m.fp, m.fn) == (0, 0, 0)
    assert pq_from_counts(0, 0, 0, 0.0)["PQ"] == 1.0


def test_pred_on_gt_frac_separates_a_fragment_from_a_hallucination():
    gt = np.zeros((40, 80), np.int32); gt[5:35, 5:35] = 1
    pred = np.zeros_like(gt)
    pred[5:15, 5:35] = 1                   # a fragment inside the object, IoU 1/3
    pred[5:35, 50:70] = 2                  # nowhere near any object
    m = match_instances(gt, pred)
    frac = dict(zip(m.pred_ids.tolist(), m.pred_on_gt_frac.tolist()))
    assert m.tp == 0 and frac[1] == pytest.approx(1.0) and frac[2] == 0.0


@pytest.mark.parametrize("seed", range(4))
def test_fast_valid_filter_equals_the_reference_implementation(seed):
    rng = np.random.default_rng(seed)
    pred = _random_blobs(rng)
    valid = rng.random(pred.shape) < 0.5
    valid[:, :48] = True
    assert np.array_equal(filter_by_valid(pred, valid, 0.5),
                          im.filter_by_valid(pred, valid, 0.5))
