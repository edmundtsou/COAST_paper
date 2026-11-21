"""Transporter handoffs along an axis: where an early member of a family gives way to a late one."""
from __future__ import annotations

import numpy as np


def scaled_profile(curve):
    """Min-max scale over finite values; constant or empty curves give NaN."""
    c = np.asarray(curve, float)
    ok = np.isfinite(c)
    out = np.full(c.shape, np.nan)
    if ok.sum() < 2:
        return out
    lo, hi = c[ok].min(), c[ok].max()
    if hi <= lo:
        return out
    out[ok] = (c[ok] - lo) / (hi - lo)
    return out


def crossing(early, late, grid):
    """First x where early - late goes from > 0 to <= 0 (linearly interpolated); NaN if never."""
    d = np.asarray(early, float) - np.asarray(late, float)
    g = np.asarray(grid, float)
    for i in range(len(d) - 1):
        if np.isfinite(d[i]) and np.isfinite(d[i + 1]) and d[i] > 0 >= d[i + 1]:
            return float(g[i] if d[i + 1] == d[i] else g[i] + (g[i + 1] - g[i]) * (-d[i]) / (d[i + 1] - d[i]))
    return np.nan
