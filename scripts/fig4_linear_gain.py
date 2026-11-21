"""Fig. 4b ranking: how much more of each gene's deviance the curve explains than straight lines through the clusters.

Same units, genes and axes as fig4_screen.py; every fit is COAST's NB GLM (coast.tl._nb_fit / _nb_lr, the model of
coast.tl.test_genes). Per gene and control mouse:
- straight lines: NB on [1, x, (x - c2)+], c2 = S2 centre on the axis ((b12 + b23) / 2), i.e. a piecewise-linear
  curve through the three segment centres, extended linearly at both ends;
- curve: COAST's test spline (coast.tl._spline, cubic B-spline with BASIS_DF columns) plus (x - c2)+, so the straight
  lines are nested in it;
- gain = (D_lines - D_curve) / D_intercept, deviances of COAST's NB GLM (dispersion from coast.tl._nb_fit under the
  curve design, as coast.tl._nb_lr).
The rank uses the smaller gain of the two mice.

  python scripts/fig4_linear_gain.py [--results-root <dir>] [--jobs 8]

Writes <results-root>/paper_figures/fig4/screen/linear_gain.csv (one row per screened gene, highest gain first).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fig3_common import RUNS  # noqa: E402
from fig4_screen import BASIS_DF, MICE, MIN_DETECTED, PT, boundary, quantile_axis  # noqa: E402


def designs(x: np.ndarray, c2: float) -> dict:
    from coast.tl import _spline
    hinge = np.maximum(x - c2, 0)[:, None]
    return {'intercept': np.ones((len(x), 1)), 'lines': np.column_stack([np.ones_like(x), x, hinge]),
            'curve': np.column_stack([np.asarray(_spline(x, BASIS_DF)), hinge])}


def one_gene(y, d, off):
    """Deviances of the intercept, the lines and the curve under COAST's NB model (dispersion from coast.tl._nb_fit
    under the curve design, deviances of the NB GLM at it, as coast.tl._nb_lr computes them), and the lines'
    coefficients."""
    import warnings

    import statsmodels.api as sm
    from coast.tl import _nb_fit

    _, alpha, conv = _nb_fit(y, d['curve'], off)
    family = sm.families.NegativeBinomial(alpha=alpha)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            fits = {n: sm.GLM(y, d[n], family=family, offset=off).fit() for n in ('intercept', 'lines', 'curve')}
    except (ValueError, np.linalg.LinAlgError):
        return None
    return ({n: f.deviance for n, f in fits.items()}, np.asarray(fits['lines'].params, float),
            bool(fits['lines'].converged and fits['curve'].converged))


def main(argv=None):
    import anndata as ad
    from scipy import sparse
    from joblib import Parallel, delayed

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--results-root', default=str(REPO / 'results'))
    p.add_argument('--jobs', type=int, default=8)
    args = p.parse_args(argv)
    root = Path(args.results_root)

    qc = ad.read_h5ad(root / RUNS['aki'] / '02_qc/units_qc.h5ad')
    ref = pd.read_parquet(root / RUNS['aki'] / '04_pseudospace/pseudospace.parquet')
    ref = ref.set_index('obs_name') if 'obs_name' in ref.columns else ref
    pt = ref[ref['sample'].astype(str).isin(MICE) & ref.segment_class.astype(str).isin(PT)]
    units = pt.index.to_numpy()
    counts = sparse.csr_matrix(qc[units].layers['counts'])
    mt = qc.var['mt'].to_numpy(bool)
    lib = np.asarray(counts[:, ~mt].sum(1)).ravel()
    sample = pt['sample'].astype(str).to_numpy()
    label = pt.segment_class.astype(str).map(PT).to_numpy()
    detected = np.ones(qc.n_vars, bool)
    for m in MICE:
        detected &= np.asarray((counts[sample == m] > 0).mean(0)).ravel() >= MIN_DETECTED
    keep = detected & ~mt
    genes = qc.var_names[keep]
    x = quantile_axis(pt['pseudospace'].to_numpy(float), np.ones(len(pt), bool))
    c2 = (boundary(x, label, 0) + boundary(x, label, 1)) / 2
    sub = counts[:, np.flatnonzero(keep)]
    fits = {}
    for m in MICE:
        k = sample == m
        y, d, off = sub[k].toarray(), designs(x[k], c2), np.log(lib[k])
        fits[m] = Parallel(n_jobs=args.jobs)(delayed(one_gene)(y[:, j], d, off) for j in range(y.shape[1]))
    rows = []
    for j, g in enumerate(genes):
        row = {'gene': g, 'c2': c2}
        for m in MICE:
            f = fits[m][j]
            if f is None:
                row.update({f'gain_{m}': np.nan, f'lines_explained_{m}': np.nan,
                            **{f'lines_b{i}_{m}': np.nan for i in range(3)}})
                continue
            dev, beta, conv = f
            d0, dl, dc = dev['intercept'], dev['lines'], dev['curve']
            row.update({f'gain_{m}': (dl - dc) / d0 if conv else np.nan, f'lines_explained_{m}': 1 - dl / d0,
                        **{f'lines_b{i}_{m}': beta[i] for i in range(3)}})
        rows.append(row)

    df = pd.DataFrame(rows)
    df['gain'] = df[[f'gain_{m}' for m in MICE]].min(1)
    # nested fits: the curve can only lower the deviance. IRLS stops at a tolerance, so a gain just below zero is
    # rounding (set to 0); one below -1e-3 of the intercept deviance means a fit failed (unranked)
    neg = df['gain'] < 0
    print(f"gains below 0: {int(neg.sum())}, lowest {df['gain'].min():.2e}", flush=True)
    df.loc[neg & (df['gain'] > -1e-3), 'gain'] = 0.0
    df.loc[df['gain'] < 0, 'gain'] = np.nan    # a failed nested fit: the gene is left unranked
    df.sort_values('gain', ascending=False).to_csv(root / 'paper_figures/fig4/screen/linear_gain.csv', index=False)
    print(df.sort_values('gain', ascending=False).head(15)[['gene', 'gain']].to_string(index=False))


if __name__ == '__main__':
    main()
