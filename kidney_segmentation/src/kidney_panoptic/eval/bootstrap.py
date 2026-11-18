"""Confidence intervals by cluster bootstrap.

Objects on a slide are not independent draws: neighbouring tubules share staining, section
thickness and focus, and a merge takes out two objects at once. Resampling objects would
treat 98 objects as 98 independent observations and return an interval that is too narrow.
The resampling unit here is therefore the CLUSTER (a spatial tile), resampled with
replacement inside each stratum (a slide), and every replicate recomputes the statistic from
the resampled clusters' raw counts — so a ratio such as PQ is bootstrapped as a ratio, not
as a mean of per-tile ratios.

What this does NOT give: an interval over slides, animals or scanners. With one or two
slides per cohort the between-slide variance cannot be estimated at all, and
``between_unit_summary`` says so rather than printing a standard error from n = 2.
"""
from __future__ import annotations

from typing import Callable, Optional, Sequence

import numpy as np

MIN_UNITS_FOR_SE = 5


def cluster_bootstrap(
    n_clusters: int,
    stat_fn: Callable[[np.ndarray], dict],
    *,
    strata: Optional[Sequence] = None,
    n_boot: int = 2000,
    seed: int = 1337,
    alpha: float = 0.05,
) -> dict:
    """Percentile bootstrap interval for every statistic ``stat_fn`` returns.

    ``stat_fn(idx)`` takes an integer array of cluster indices (with repeats) and returns
    ``{name: float}``. Replicates where a statistic is undefined (NaN) are dropped for that
    statistic and the number kept is reported, so a rarely-defined statistic cannot pass off
    a handful of replicates as a full interval.
    """
    point = stat_fn(np.arange(n_clusters))
    out = {k: {"estimate": _f(v), "ci_low": None, "ci_high": None, "se": None,
               "n_boot": 0} for k, v in point.items()}
    if n_clusters < 2 or n_boot <= 0:
        return out

    strata_arr = np.zeros(n_clusters, np.int64) if strata is None else \
        np.unique(np.asarray(strata), return_inverse=True)[1]
    groups = [np.flatnonzero(strata_arr == s) for s in np.unique(strata_arr)]

    rng = np.random.default_rng(seed)
    draws: dict[str, list[float]] = {k: [] for k in point}
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])
        for k, v in stat_fn(idx).items():
            draws[k].append(v)

    lo_q, hi_q = 100 * alpha / 2, 100 * (1 - alpha / 2)
    for k, vals in draws.items():
        v = np.asarray(vals, float)
        v = v[np.isfinite(v)]
        out[k]["n_boot"] = int(v.size)
        if v.size >= 2:
            out[k]["ci_low"] = float(np.percentile(v, lo_q))
            out[k]["ci_high"] = float(np.percentile(v, hi_q))
            out[k]["se"] = float(v.std(ddof=1))
    return out


def between_unit_summary(values: Sequence[float], alpha: float = 0.05) -> dict:
    """Mean, standard error and t-interval across independent units (slides).

    Below ``MIN_UNITS_FOR_SE`` units only the mean and range are returned: a standard error
    from two or three slides is itself almost pure noise and reads as more than it is.
    """
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], float)
    out = {"n": int(v.size), "mean": _f(v.mean()) if v.size else None,
           "min": _f(v.min()) if v.size else None, "max": _f(v.max()) if v.size else None,
           "se": None, "ci_low": None, "ci_high": None}
    if v.size >= MIN_UNITS_FOR_SE:
        from scipy import stats

        se = float(v.std(ddof=1) / np.sqrt(v.size))
        half = float(stats.t.ppf(1 - alpha / 2, v.size - 1)) * se
        out.update(se=se, ci_low=float(v.mean() - half), ci_high=float(v.mean() + half))
    return out


def _f(v) -> Optional[float]:
    return float(v) if v is not None and np.isfinite(v) else None
