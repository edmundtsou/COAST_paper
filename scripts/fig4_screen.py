"""Fig. 4 screen: genes whose pattern along PT the S1/S2/S3 means and the bulk mean cannot express.

Control PT units of the control/AKI fit, on COAST's coordinate as a quantile of these units (x). Every gene is
fitted in each control mouse by NB GLMs: bulk, clusters (S1/S2/S3), clusters + curve, curve.
Category 1 is a peak between segments, category 2 a change within a segment; both need the curve to beat the
clusters in both mice at a decoy-calibrated 5% threshold. Tests and curves use COAST (coast.tl.test_genes, and the
penalised NB GAM coast.tl.fit_curves, 2026-11-15; before, an unpenalised 6-df B-spline drew the curves). Curves
and bin means cover the 5th-95th percentile of x, COAST's range (2026-11-15). Protocol (frozen before this ran):

  python scripts/fig4_screen.py [--results-root <dir>] [--jobs 8]

Writes <results-root>/paper_figures/fig4/screen/: genes.csv (one row per screened gene), curves.npz (curves,
cluster means, bulk and bin means of every screened gene in each mouse), axes.csv (boundaries of each axis).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fig3_common import RUNS  # noqa: E402

MICE = ['Ctrl1A2', 'Ctrl1A4']
PT = {'PT-S1': 0, 'PT-S2': 1, 'PT-S3': 2}
NEIGHBOURS = {'mTAL': 'AL', 'cTAL': 'AL', 'Macula-densa': 'AL', 'DCT1': 'DCT', 'DCT2': 'DCT',
              'CCD': 'CD', 'OMCD': 'CD', 'IMCD': 'CD'}
MIN_DETECTED = 0.10        # share of PT units with a count, in each mouse
MARGIN = 0.06              # cores lie further than this from a boundary; the transition window lies within it
PEAK_LOG2, CHANGE_LOG2 = 0.5, 1.0
FDR = 0.05
NEIGHBOUR_RATIO = 2.0
BASIS_DF, GRID, N_BINS = 6, np.linspace(0, 1, 201), 20


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--results-root', default=str(REPO / 'results'))
    p.add_argument('--out', default='paper_figures/fig4/screen', help='relative to the results root')
    p.add_argument('--jobs', type=int, default=8)
    return p.parse_args(argv)


def quantile_axis(t: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """COAST's coordinate as a quantile of the reference units, (rank - 0.5) / n; the other units are mapped through
    that distribution (as in the COAST tutorials)."""
    x = np.empty(len(t))
    x[reference] = (pd.Series(t[reference]).rank(method='average').to_numpy() - 0.5) / reference.sum()
    order = np.argsort(t[reference])
    x[~reference] = np.interp(t[~reference], t[reference][order], x[reference][order])
    return x


def boundary(x: np.ndarray, label: np.ndarray, lo: int) -> float:
    """Threshold on x misclassifying the fewest units between labels lo and lo + 1."""
    k = (label == lo) | (label == lo + 1)
    xs, hi = x[k], label[k] == lo + 1
    order = np.argsort(xs)
    xs, hi = xs[order], hi[order]
    # errors at a cut after position i: lo-units above it + hi-units at or below it
    err = (~hi[::-1]).cumsum()[::-1] - ~hi + hi.cumsum()
    i = int(np.argmin(err))
    return float((xs[i] + xs[min(i + 1, len(xs) - 1)]) / 2)


def shuffle_within(x: np.ndarray, label: np.ndarray, rng) -> np.ndarray:
    out = x.copy()
    for g in np.unique(label):
        idx = np.flatnonzero(label == g)
        out[idx] = x[rng.permutation(idx)]
    return out


def log2_cp10k(eta: np.ndarray) -> np.ndarray:
    return (eta + np.log(1e4)) / np.log(2)


def _glm_one(y, design, offset):
    """COAST's NB model as in coast.tl._nb_lr: dispersion from coast.tl._nb_fit, coefficients from the NB GLM at it."""
    import warnings

    import statsmodels.api as sm
    from coast.tl import _nb_fit

    _, alpha, _ = _nb_fit(y, design, offset)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            fit = sm.GLM(y, design, family=sm.families.NegativeBinomial(alpha=alpha), offset=offset).fit()
        return np.asarray(fit.params, float), bool(fit.converged)
    except (ValueError, np.linalg.LinAlgError):
        return np.full(design.shape[1], np.nan), False


def glm_means(y, design, offset, jobs):
    """Log rates of each design column per gene from COAST's NB model (dispersion by coast.tl._nb_fit, coefficients by
    the GLM at that dispersion, as inside coast.tl.test_genes): {'beta': genes x columns, 'converged': genes}."""
    from joblib import Parallel, delayed

    fits = Parallel(n_jobs=jobs)(delayed(_glm_one)(y[:, j], design, offset) for j in range(y.shape[1]))
    return {'beta': np.array([f[0] for f in fits], dtype=float).reshape(y.shape[1], design.shape[1]),
            'converged': np.array([f[1] for f in fits], bool)}


def fit_axis(counts, lib, x, label, sample, genes, seed, jobs):
    """COAST fits (github.com/edmundtsou/COAST): in each mouse, the likelihood ratio of clusters + spline
    over clusters against a decoy shuffled within clusters (coast.tl.test_genes); the curve of both mice from the
    penalised NB GAM (coast.tl.fit_curves, shared knots and smoothing); cluster and bulk means by COAST's NB GLM.
    counts: units x genes (sparse)."""
    import anndata as ad
    import coast

    a = ad.AnnData(counts.tocsr().astype(np.float32), obs=pd.DataFrame(
        {'x': x, 'label': pd.Categorical(label), 'sample': pd.Categorical(sample), 'lib': lib}))
    a.var_names = list(genes)
    a.layers['counts'] = a.X
    curves = coast.tl.fit_curves(a, genes, x='x', sample_key='sample', library='lib', limits=(GRID[0], GRID[-1]),
                                 n_points=len(GRID), n_jobs=jobs)
    # COAST's range (coast.tl.fit_curves default, coast.pl.genes): curves and bin means only between the 5th and 95th
    # percentile of x over all units; evaluated on the fixed GRID so both mice share columns
    lo, hi = np.percentile(x, [5, 95])
    curves.loc[:, (GRID < lo) | (GRID > hi)] = np.nan
    out = {}
    for m in MICE:
        k = sample == m
        test = coast.tl.test_genes(a[k], x='x', groupby='label', genes=genes, library='lib', df=BASIS_DF, fdr=FDR, seed=seed,
                                   n_jobs=jobs)
        y = a.layers['counts'][k].toarray()
        off, onehot = np.log(lib[k]), np.eye(3)[label[k]]
        clusters, bulk = glm_means(y, onehot, off, jobs), glm_means(y, np.ones((k.sum(), 1)), off, jobs)
        inside = np.flatnonzero((x[k] >= lo) & (x[k] <= hi))
        bins = np.array_split(inside[np.argsort(x[k][inside])], N_BINS)
        with np.errstate(divide='ignore'):
            bin_means = np.stack([np.log2(1e4 * y[b].sum(0) / lib[k][b].sum()) for b in bins], 1)
        out[m] = {'lr': test.lr.to_numpy(), 'decoy_lr': test.decoy_lr.to_numpy(),
                  'significant': test.significant.to_numpy(bool), 'threshold': float(test.attrs['threshold']),
                  'converged': test.converged.to_numpy(bool) & clusters['converged']
                  & np.isfinite(curves.loc[m].reindex(genes).to_numpy(float)).any(1),
                  'curve': curves.loc[m].reindex(genes).to_numpy(float),
                  'clusters': log2_cp10k(clusters['beta']), 'bulk': log2_cp10k(bulk['beta'][:, 0]),
                  'bins': bin_means, 'bin_x': np.array([x[k][b].mean() for b in bins])}
    return out


def shape_calls(curve: np.ndarray, b12: float, b23: float) -> dict:
    """Category 1 and 2 shape criteria of one curve (log2 on GRID)."""
    cores = [(0.0, b12 - MARGIN), (b12 + MARGIN, b23 - MARGIN), (b23 + MARGIN, 1.0)]
    core_mean = [np.nanmean(curve[(GRID >= lo) & (GRID <= hi)]) for lo, hi in cores]
    i = int(np.nanargmax(curve))
    xp = GRID[i]
    peak_at = 12 if abs(xp - b12) <= MARGIN else 23 if abs(xp - b23) <= MARGIN else 0
    flank = {12: (0, 1), 23: (1, 2)}.get(peak_at)
    height = curve[i] - max(core_mean[flank[0]], core_mean[flank[1]]) if flank else np.nan
    changes = []
    for lo, hi in cores:
        third = (hi - lo) / 3
        first = np.nanmean(curve[(GRID >= lo) & (GRID <= lo + third)])
        last = np.nanmean(curve[(GRID >= hi - third) & (GRID <= hi)])
        changes.append(last - first)
    seg = int(np.argmax(np.abs(changes)))
    return {'peak_x': xp, 'peak_at': peak_at, 'peak_height': height, 'change_segment': seg,
            'change': changes[seg], 'changes': changes, 'core_mean': core_mean}


def main(argv=None):
    import anndata as ad
    from scipy import sparse
    args = parse_args(argv)
    root = Path(args.results_root)
    out = root / args.out
    out.mkdir(parents=True, exist_ok=True)

    qc = ad.read_h5ad(root / RUNS['aki'] / '02_qc/units_qc.h5ad')
    ref = pd.read_parquet(root / RUNS['aki'] / '04_pseudospace/pseudospace.parquet')
    ref = ref.set_index('obs_name') if 'obs_name' in ref.columns else ref
    ctrl = ref[ref['sample'].astype(str).isin(MICE)]
    pt = ctrl[ctrl.segment_class.astype(str).isin(PT)]
    units = pt.index.to_numpy()

    counts = sparse.csr_matrix(qc[units].layers['counts'])
    mt = qc.var['mt'].to_numpy(bool)
    lib = np.asarray(counts[:, ~mt].sum(1)).ravel()
    sample = pt['sample'].astype(str).to_numpy()
    label = pt.segment_class.astype(str).map(PT).to_numpy()

    detected = np.ones(qc.n_vars, bool)
    for m in MICE:
        k = sample == m
        detected &= np.asarray((counts[k] > 0).mean(0)).ravel() >= MIN_DETECTED
    keep = detected & ~mt
    genes = qc.var_names[keep]

    # neighbour filter: counts per 10k in AL, DCT and CD units of the control sections against PT
    nb = ctrl[ctrl.segment_class.astype(str).isin(NEIGHBOURS)]
    nbc = sparse.csr_matrix(qc[nb.index.to_numpy()].layers['counts'])[:, keep]
    nblib = np.asarray(sparse.csr_matrix(qc[nb.index.to_numpy()].layers['counts'])[:, ~mt].sum(1)).ravel()
    pt_rate = np.asarray(counts[:, keep].sum(0)).ravel() / lib.sum()
    group = nb.segment_class.astype(str).map(NEIGHBOURS).to_numpy()
    nb_rate = {g: np.asarray(nbc[group == g].sum(0)).ravel() / nblib[group == g].sum() for g in ('AL', 'DCT', 'CD')}
    neighbour_ratio = np.max(np.stack(list(nb_rate.values())), 0) / np.maximum(pt_rate, 1e-12)

    x = quantile_axis(pt['pseudospace'].to_numpy(float), np.ones(len(pt), bool))
    b12, b23 = boundary(x, label, 0), boundary(x, label, 1)
    fits = fit_axis(counts[:, np.flatnonzero(keep)], lib, x, label, sample, genes, 0, args.jobs)
    rows, store = [], {m: {} for m in MICE}
    for j, g in enumerate(genes):
        row = {'gene': g, 'b12': b12, 'b23': b23, 'neighbour_ratio': float(neighbour_ratio[j])}
        for m in MICE:
            f = fits[m]
            s = shape_calls(f['curve'][j], b12, b23)
            row.update({f'lr_{m}': f['lr'][j], f'decoy_lr_{m}': f['decoy_lr'][j],
                        f'converged_{m}': bool(f['converged'][j]), f'beyond_{m}': bool(f['converged'][j] & f['significant'][j]),
                        f'peak_x_{m}': s['peak_x'], f'peak_at_{m}': s['peak_at'], f'peak_height_{m}': s['peak_height'],
                        f'change_segment_{m}': s['change_segment'], f'change_{m}': s['change'], f'bulk_{m}': f['bulk'][j]})
            row.update({f'cluster_S{i + 1}_{m}': f['clusters'][j, i] for i in range(3)})
            store[m][g] = (f['curve'][j], f['clusters'][j], f['bulk'][j], f['bins'][j], f['bin_x'])
        rows.append(row)

    df = pd.DataFrame(rows)
    thresholds = {m: fits[m]['threshold'] for m in MICE}
    a, b = MICE
    df['beyond_both'] = df[f'beyond_{a}'] & df[f'beyond_{b}']
    df['neighbour_ok'] = df['neighbour_ratio'] <= NEIGHBOUR_RATIO
    df['cat1'] = (df.beyond_both & df.neighbour_ok & (df[f'peak_at_{a}'] > 0) & (df[f'peak_at_{a}'] == df[f'peak_at_{b}'])
                  & (df[f'peak_height_{a}'] >= PEAK_LOG2) & (df[f'peak_height_{b}'] >= PEAK_LOG2))
    df['cat2'] = (df.beyond_both & df.neighbour_ok & (df[f'change_segment_{a}'] == df[f'change_segment_{b}'])
                  & (np.sign(df[f'change_{a}']) == np.sign(df[f'change_{b}']))
                  & (df[f'change_{a}'].abs() >= CHANGE_LOG2) & (df[f'change_{b}'].abs() >= CHANGE_LOG2))
    df['cat1_score'] = df[[f'peak_height_{a}', f'peak_height_{b}']].min(1)
    df['cat2_score'] = df[[f'change_{a}', f'change_{b}']].abs().min(1)
    df.to_csv(out / 'genes.csv', index=False)
    pd.DataFrame([{'n_units': len(x), 'b12': b12, 'b23': b23}]).to_csv(out / 'axes.csv', index=False)

    keep_genes = df.loc[df.cat1 | df.cat2 | df.beyond_both, 'gene'].tolist()
    np.savez_compressed(out / 'curves.npz', grid=GRID, genes=np.array(keep_genes), **{
        f'{part}|{m}': np.stack([store[m][g][i] for g in keep_genes]) if keep_genes else np.empty(0)
        for m in MICE for i, part in enumerate(('curve', 'clusters', 'bulk', 'bins', 'bin_x'))})
    summary = {'n_units': {m: int((sample == m).sum()) for m in MICE}, 'n_genes_screened': int(len(df)),
               'thresholds': thresholds,
               'n_beyond': {m: int(df[f'beyond_{m}'].sum()) for m in MICE}, 'n_beyond_both': int(df.beyond_both.sum()),
               'n_neighbour_dropped': int((df.beyond_both & ~df.neighbour_ok).sum()),
               'n_cat1': int(df.cat1.sum()), 'n_cat2': int((df.cat2 & ~df.cat1).sum()),
               'n_cat1_by_boundary': df.loc[df.cat1, f'peak_at_{a}'].value_counts().to_dict(),
               'n_cat2_by_segment': (df.loc[df.cat2 & ~df.cat1, f'change_segment_{a}'] + 1).value_counts().to_dict(),
               'top_cat1': df[df.cat1].nlargest(10, 'cat1_score').gene.tolist(),
               'top_cat2': df[df.cat2 & ~df.cat1].nlargest(10, 'cat2_score').gene.tolist()}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == '__main__':
    main()
