import numpy as np
import pytest

from kidney_panoptic.eval.bootstrap import between_unit_summary, cluster_bootstrap


def _mean_of(values):
    v = np.asarray(values, float)
    return lambda idx: {"mean": float(v[idx].mean())}


def test_same_seed_gives_the_same_interval_and_a_different_seed_does_not():
    stat = _mean_of(np.random.default_rng(0).normal(size=40))
    a = cluster_bootstrap(40, stat, n_boot=300, seed=7)
    b = cluster_bootstrap(40, stat, n_boot=300, seed=7)
    c = cluster_bootstrap(40, stat, n_boot=300, seed=8)
    assert a == b
    assert a["mean"]["ci_low"] != c["mean"]["ci_low"]


def test_interval_brackets_the_estimate_and_matches_the_analytic_standard_error():
    v = np.random.default_rng(1).normal(loc=3.0, scale=2.0, size=200)
    r = cluster_bootstrap(200, _mean_of(v), n_boot=1500, seed=1)["mean"]
    assert r["ci_low"] < r["estimate"] < r["ci_high"]
    assert r["estimate"] == pytest.approx(v.mean())
    assert r["se"] == pytest.approx(v.std(ddof=1) / np.sqrt(200), rel=0.10)


def test_coverage_is_close_to_nominal():
    """A 95 % interval should contain the true mean in roughly 95 % of repeated samples."""
    rng = np.random.default_rng(2)
    hits = 0
    for rep in range(200):
        v = rng.normal(size=60)
        r = cluster_bootstrap(60, _mean_of(v), n_boot=300, seed=rep)["mean"]
        hits += r["ci_low"] <= 0.0 <= r["ci_high"]
    assert 0.88 <= hits / 200 <= 0.99


def test_ratio_is_bootstrapped_as_a_ratio_of_sums():
    """One cluster with thirty objects must outweigh one with a single object."""
    num = np.array([30.0, 0.0])
    den = np.array([30.0, 1.0])
    r = cluster_bootstrap(2, lambda i: {"rate": float(num[i].sum() / den[i].sum())},
                          n_boot=50, seed=0)["rate"]
    assert r["estimate"] == pytest.approx(30 / 31), "not the 0.5 a mean of ratios would give"


def test_resampling_stays_inside_each_stratum():
    """With slides as strata every replicate keeps each slide's tile count."""
    strata = ["a"] * 5 + ["b"] * 3
    seen = []
    cluster_bootstrap(8, lambda i: seen.append(np.sort(i)) or {"x": 0.0}, strata=strata,
                      n_boot=40, seed=0)
    for idx in seen[1:]:
        assert (idx < 5).sum() == 5 and (idx >= 5).sum() == 3


def test_undefined_replicates_are_dropped_and_counted():
    v = np.array([1.0, np.nan, 2.0, 3.0])
    stat = lambda i: {"m": float(v[i].mean())}                      # noqa: E731
    r = cluster_bootstrap(4, stat, n_boot=200, seed=0)["m"]
    assert r["estimate"] is None
    assert 0 < r["n_boot"] < 200 and np.isfinite(r["ci_low"])


def test_one_cluster_gives_an_estimate_and_no_interval():
    r = cluster_bootstrap(1, _mean_of([4.0]), n_boot=100)["mean"]
    assert r["estimate"] == 4.0 and r["ci_low"] is None and r["se"] is None


def test_between_slide_standard_error_is_withheld_below_five_slides():
    few = between_unit_summary([0.80, 0.86])
    assert few["n"] == 2 and few["mean"] == pytest.approx(0.83)
    assert few["se"] is None and few["ci_low"] is None

    many = between_unit_summary([0.80, 0.82, 0.84, 0.86, 0.88])
    assert many["se"] == pytest.approx(np.std([0.80, 0.82, 0.84, 0.86, 0.88], ddof=1) / 5 ** 0.5)
    assert many["ci_low"] < 0.84 < many["ci_high"]
