"""Fig. 6 screen: control against AKI along the PT, on COAST's coordinate of the control/AKI fit.

x is COAST's coordinate of the control/AKI fit as a quantile of the control PT units (IR units are mapped through
the control distribution), one axis for every gene. Per gene and mouse, COAST gives the curve (coast.tl.fit_curves,
penalised, fitted with the other mice; 5th-95th percentile of x) and its NB GLM the S1/S2/S3 means and the bulk mean
(2026-11-15; before, an unpenalised B-spline per mouse). From those:
 category A   genes whose AKI response changes inside a segment (rules 1-5, decoy-calibrated)
 handoffs     the frozen transporter pairs (inputs/handoff_pairs.csv), mouse: crossing positions in each mouse, shifts with bootstrap intervals
 programs     transport (T_PT), cell cycle (C) and injury response (R) programs (inputs/), profiled on this axis
 pathways     a within-segment set screen against random sets, calibrated on the two relabelings

  OMP_NUM_THREADS=1 python scripts/fig6_screen.py --jobs 12
Writes <results-root>/paper_figures/fig6/screen/.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig4_screen as fs  # noqa: E402
from fig3_common import RUNS  # noqa: E402

CONTROLS, INJURED = ['Ctrl1A2', 'Ctrl1A4'], ['IR2A2', 'IR2A4']
MICE = CONTROLS + INJURED
# the three balanced 2-vs-2 splits; each one's "pairs" are its four cross differences
SPLITS = {'condition': (INJURED, CONTROLS), 'relabeling 1': (['IR2A2', 'Ctrl1A2'], ['IR2A4', 'Ctrl1A4']),
          'relabeling 2': (['IR2A2', 'Ctrl1A4'], ['IR2A4', 'Ctrl1A2'])}
CHANGE_LOG2, PAIR_LOG2, LABEL_LOG2 = 1.0, 0.5, 0.5
SPECIFIC = 0.25
MIN_SUPPORT = 25
MAX_FALSE_SHARE = 0.10
SHIFT_MIN, N_BOOT = 0.05, 200
# post hoc (2026-11-12, as Fig. 5 on 2026-11-11): a mouse's crossing counts only if both partners change at least 2-fold
# (1 log2) on its curve over the mouse's x range; min-max scaling otherwise stretches a near-flat curve into a switch
AMP_LOG2 = 1.0
MIN_SET, N_RANDOM_SETS, SET_Q = 10, 1000, 0.05
GRID = fs.GRID


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--results-root', default=str(REPO / 'results'))
    p.add_argument('--out', default='paper_figures/fig6/screen', help='relative to the results root')
    p.add_argument('--jobs', type=int, default=8)
    p.add_argument('--handoffs-only', action='store_true',
                   help='fit only the handoff genes and stop after handoffs.csv (the fits are deterministic, so the '
                        'handoff rows match a full run; use a separate --out)')
    p.add_argument('--smoke', action='store_true', help='two axes, few bootstraps and random sets (code check only)')
    return p.parse_args(argv)


def split_value(q: dict, split: str):
    plus, minus = SPLITS[split]
    return np.mean([q[m] for m in plus], 0) - np.mean([q[m] for m in minus], 0)


def split_pairs(q: dict, split: str):
    plus, minus = SPLITS[split]
    return np.stack([q[a] - q[b] for a in plus for b in minus])


def cores(b12, b23):
    return [(0.0, b12 - fs.MARGIN), (b12 + fs.MARGIN, b23 - fs.MARGIN), (b23 + fs.MARGIN, 1.0)]


def thirds(lo, hi):
    t = (hi - lo) / 3
    return (lo, lo + t), (hi - t, hi)


def within_core(curves: np.ndarray, b12, b23) -> np.ndarray:
    """Last third minus first third of each core, per curve on GRID: (..., 3)."""
    out = []
    for lo, hi in cores(b12, b23):
        (a0, a1), (z0, z1) = thirds(lo, hi)
        with warnings.catch_warnings():   # NaN outside COAST's 5-95 % range: the windows are clipped to it
            warnings.simplefilter('ignore', RuntimeWarning)
            first = np.nanmean(curves[..., (GRID >= a0) & (GRID <= a1)], -1)
            last = np.nanmean(curves[..., (GRID >= z0) & (GRID <= z1)], -1)
        out.append(last - first)
    return np.stack(out, -1)


def label_thirds(counts, lib, x, label, b12, b23):
    """Per core: log2 rate (summed counts + 0.5, per 10k) over units of that label in the first and last thirds,
    and the number of units in each: rates (G, 3, 2), n (3, 2)."""
    rates, n = [], []
    for s, (lo, hi) in enumerate(cores(b12, b23)):
        r, c = [], []
        for a, b in thirds(lo, hi):
            k = (label == s) & (x >= a) & (x <= b)
            r.append(np.log2(1e4 * (np.asarray(counts[k].sum(0)).ravel() + 0.5) / max(lib[k].sum(), 1.0)))
            c.append(int(k.sum()))
        rates.append(np.stack(r, 1))
        n.append(c)
    return np.stack(rates, 1), np.array(n)


def core_zero(counts, x, b12, b23):
    """(G, 3): True where a gene has no count at all in the first or the last third of a core (all units there).
    A spline there is unsupported and can dive without bound (post-hoc rule, see the protocol doc)."""
    out = []
    for lo, hi in cores(b12, b23):
        z = np.zeros(counts.shape[1], bool)
        for a, b in thirds(lo, hi):
            k = (x >= a) & (x <= b)
            z |= np.asarray(counts[k].sum(0)).ravel() == 0
        out.append(z)
    return np.stack(out, 1)


def coast_curves(y, lib, x, sample, genes, jobs):
    """COAST's penalised NB GAM (coast.tl.fit_curves: one curve per section, knots, smoothing and dispersion shared by
    the sections fitted together) on GRID, log2 CP10k; NaN outside the 5th-95th percentile of x over these units (COAST's
    range) and outside a section's own range. Returns {section: genes x GRID}."""
    import anndata as ad
    import coast

    a = ad.AnnData(np.asarray(y, dtype=np.float32),
                   obs=pd.DataFrame({'x': x, 'sample': pd.Categorical(sample), 'lib': lib}))
    a.var_names = [str(g) for g in genes]
    a.layers['counts'] = a.X
    c = coast.tl.fit_curves(a, list(a.var_names), x='x', sample_key='sample', library='lib',
                            limits=(GRID[0], GRID[-1]), n_points=len(GRID), n_jobs=jobs)
    lo, hi = np.percentile(x, [5, 95])
    c.loc[:, (GRID < lo) | (GRID > hi)] = np.nan
    return {s: c.loc[s].reindex(a.var_names).to_numpy(float) for s in pd.unique(sample)}


def fit_sections(y, lib, x, label, sample, genes, sections, jobs, decoy_rng=None):
    """Per section: COAST curve (fitted with the other sections), S1/S2/S3 and bulk means from COAST's NB GLM
    (fs.glm_means), equal-count bin means within COAST's 5-95 % range; with decoy_rng also the curve of x shuffled
    within labels in each section ('decoy', 'xs')."""
    curves = coast_curves(y, lib, x, sample, genes, jobs)
    if decoy_rng is not None:
        xs = x.copy()
        for m in sections:
            k = sample == m
            xs[k] = fs.shuffle_within(x[k], label[k], decoy_rng)
        decoys = coast_curves(y, lib, xs, sample, genes, jobs)
    lo, hi = np.percentile(x, [5, 95])
    out = {}
    for m in sections:
        k = sample == m
        yk, off, xk = y[k], np.log(lib[k]), x[k]
        clusters = fs.glm_means(yk, np.eye(3)[label[k]], off, jobs)
        bulk = fs.glm_means(yk, np.ones((k.sum(), 1)), off, jobs)
        inside = np.flatnonzero((xk >= lo) & (xk <= hi))
        bins = np.array_split(inside[np.argsort(xk[inside])], fs.N_BINS)
        with np.errstate(divide='ignore'):
            bin_means = np.stack([np.log2(1e4 * yk[b].sum(0) / lib[k][b].sum()) for b in bins], 1)
        out[m] = {'curve': curves[m], 'converged': clusters['converged'] & np.isfinite(curves[m]).any(1),
                  'clusters': fs.log2_cp10k(clusters['beta']), 'bulk': fs.log2_cp10k(bulk['beta'][:, 0]),
                  'bins': bin_means, 'bin_x': np.array([xk[b].mean() for b in bins])}
        if decoy_rng is not None:
            out[m].update({'decoy': decoys[m], 'xs': xs[k]})
    return out


def category_a(W: dict, L: dict, support_ok: np.ndarray, split: str = 'condition') -> np.ndarray:
    """Rules 1-5 for one split. W, L: {mouse: (G, 3)} curve and within-label changes; returns (G, 3) calls."""
    w = split_value(W, split)
    pairs = split_pairs(W, split)
    others = [s for s in SPLITS if s != split]
    lab = split_value(L, split)
    lab_pairs = split_pairs(L, split)
    sign = np.sign(w)
    r1 = np.abs(w) >= CHANGE_LOG2
    r2 = ((np.sign(pairs) == sign) & (np.abs(pairs) >= PAIR_LOG2)).all(0)
    r3 = np.all([np.abs(split_value(W, o)) <= SPECIFIC * np.abs(w) for o in others], 0)
    r4 = (np.sign(lab) == sign) & (np.abs(lab) >= LABEL_LOG2) & (np.sign(lab_pairs) == sign).all(0)
    return r1 & r2 & r3 & r4 & support_ok


def bh(p):
    p = np.asarray(p, float)
    order = np.argsort(p)
    q = p[order] * len(p) / np.arange(1, len(p) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty_like(q)
    out[order] = np.minimum(q, 1)
    return out


def set_screen(gene_w: dict, members: dict, rng) -> pd.DataFrame:
    """Within-segment set screen for every split. gene_w: {split or pair label: (G, 3)} over the universe, NaN
    where a gene's curve is unsupported in that segment; members: {set: index array}. Per segment, a set uses its
    supported members (at least MIN_SET) against random sets of the same size from the supported genes; two-sided
    empirical p, BH over sets x segments."""
    rows = []
    for split in SPLITS:
        w = gene_w[split]
        for s in range(3):
            valid = np.isfinite(w[:, s])
            pool = np.flatnonzero(valid)
            null = {}
            for name, idx in members.items():
                ix = idx[valid[idx]]
                if len(ix) < MIN_SET:
                    continue
                if len(ix) not in null:
                    null[len(ix)] = np.array([w[rng.choice(pool, len(ix), replace=False), s].mean()
                                              for _ in range(N_RANDOM_SETS)])
                obs, nl = w[ix, s].mean(), null[len(ix)]
                centre = nl.mean()
                p = (1 + (np.abs(nl - centre) >= abs(obs - centre)).sum()) / (1 + N_RANDOM_SETS)
                pairs = np.array([gene_w[f'{split}|{k}'][ix, s].mean() for k in range(4)])
                others = np.array([gene_w[o][ix, s].mean() for o in SPLITS if o != split])
                rows.append({'split': split, 'set': name, 'n': len(ix), 'segment': s + 1, 'W': obs, 'p': p,
                             'pairs_agree': bool((np.sign(pairs) == np.sign(obs)).all()),
                             'specific': bool((np.abs(others) <= SPECIFIC * abs(obs)).all()),
                             **{f'pair_{k}': pairs[k] for k in range(4)},
                             **{f'other_{j}': others[j] for j in range(2)}})
    df = pd.DataFrame(rows)
    df['q'] = np.nan
    for split in SPLITS:
        k = df.split == split
        df.loc[k, 'q'] = bh(df.loc[k, 'p'].to_numpy())
    df['call'] = (df.q <= SET_Q) & df.pairs_agree & df.specific
    return df


# ------------------------------------------------------------------------------------------------- main
def main(argv=None):
    import anndata as ad
    from scipy import sparse
    from coast_paper.handoffs import crossing, scaled_profile

    global N_BOOT, N_RANDOM_SETS
    args = parse_args(argv)
    root = Path(args.results_root)
    out = root / args.out
    if args.smoke:
        out, N_BOOT, N_RANDOM_SETS = out.with_name(out.name + '_smoke'), 3, 50
    out.mkdir(parents=True, exist_ok=True)

    qc = ad.read_h5ad(root / RUNS['aki'] / '02_qc/units_qc.h5ad')
    ref = pd.read_parquet(root / RUNS['aki'] / '04_pseudospace/pseudospace.parquet')
    ref = ref.set_index('obs_name') if 'obs_name' in ref.columns else ref
    pt = ref[ref['sample'].astype(str).isin(MICE) & ref.segment_class.astype(str).isin(fs.PT)]
    units = pt.index.to_numpy()
    counts = sparse.csc_matrix(qc[units].layers['counts'])
    mt = qc.var['mt'].to_numpy(bool)
    lib = np.asarray(counts[:, ~mt].sum(1)).ravel()
    sample = pt['sample'].astype(str).to_numpy()
    label = pt.segment_class.astype(str).map(fs.PT).to_numpy()

    # universe: detected in >= 10 % of PT units in each mouse of at least one condition
    det = {m: np.asarray((counts[sample == m] > 0).mean(0)).ravel() for m in MICE}
    detected = ((det[CONTROLS[0]] >= fs.MIN_DETECTED) & (det[CONTROLS[1]] >= fs.MIN_DETECTED)) | \
               ((det[INJURED[0]] >= fs.MIN_DETECTED) & (det[INJURED[1]] >= fs.MIN_DETECTED))
    universe = detected & ~mt

    # neighbour filter within each condition's sections
    ratio = {}
    for cond, mice in (('control', CONTROLS), ('IR', INJURED)):
        k = np.isin(sample, mice)
        pt_rate = np.asarray(counts[k].sum(0)).ravel() / lib[k].sum()
        nb = ref[ref['sample'].astype(str).isin(mice) & ref.segment_class.astype(str).isin(fs.NEIGHBOURS)]
        nbc = sparse.csr_matrix(qc[nb.index.to_numpy()].layers['counts'])
        nblib = np.asarray(nbc[:, ~mt].sum(1)).ravel()
        group = nb.segment_class.astype(str).map(fs.NEIGHBOURS).to_numpy()
        rates = [np.asarray(nbc[group == g].sum(0)).ravel() / nblib[group == g].sum() for g in ('AL', 'DCT', 'CD')]
        ratio[cond] = np.max(np.stack(rates), 0) / np.maximum(pt_rate, 1e-12)
    neighbour_ok = (ratio['control'] <= fs.NEIGHBOUR_RATIO) & (ratio['IR'] <= fs.NEIGHBOUR_RATIO)

    pairs_101 = pd.read_csv(REPO / 'inputs/handoff_pairs.csv')
    pairs_101 = pairs_101[(pairs_101.species == 'mouse') & pairs_101.confirmed.astype(bool)][['family', 'early', 'late']]
    poster = pd.DataFrame({'family': ['poster', 'poster'], 'early': ['Slc5a12', 'Slc5a2'], 'late': ['Slc5a8', 'Slc5a1']})
    handoff_pairs = pd.concat([pairs_101.assign(source='frozen pairs'), poster.assign(source='poster')], ignore_index=True)
    handoff_genes = sorted(set(handoff_pairs.early) | set(handoff_pairs.late))
    missing = [g for g in handoff_genes if g not in qc.var_names]
    if missing:
        print('handoff genes missing from the panel:', missing)
    handoff_genes = [g for g in handoff_genes if g in qc.var_names]
    fit_mask = np.zeros_like(universe) if args.handoffs_only else universe.copy()
    fit_mask[[qc.var_names.get_loc(g) for g in handoff_genes]] = True

    names = qc.var_names.to_numpy()
    if args.smoke:   # a few hundred genes plus the handoff genes
        fit_mask[np.flatnonzero(fit_mask)[300:]] = False
        fit_mask[[qc.var_names.get_loc(g) for g in handoff_genes]] = True
    x = fs.quantile_axis(pt['pseudospace'].to_numpy(float), np.isin(sample, CONTROLS))
    ctrl = np.isin(sample, CONTROLS)
    b12, b23 = fs.boundary(x[ctrl], label[ctrl], 0), fs.boundary(x[ctrl], label[ctrl], 1)
    lo_c, hi_c = x[ctrl].min(), x[ctrl].max()
    axis_row = {'b12': b12, 'b23': b23, **{f'n_{m}': int((sample == m).sum()) for m in MICE},
                **{f'clipped_low_{m}': float((x[sample == m] <= lo_c).mean()) for m in INJURED},
                **{f'clipped_high_{m}': float((x[sample == m] >= hi_c).mean()) for m in INJURED}}
    gi = np.flatnonzero(fit_mask)
    sub = counts[:, gi]
    rng = np.random.default_rng(0)
    fits = fit_sections(sub.toarray(), lib, x, label, sample, names[gi], MICE, args.jobs, decoy_rng=rng)
    lt, lt_decoy, support, zero, boot_inputs = {}, {}, {}, {}, {}
    hk = np.isin(names[gi], handoff_genes)
    for m in MICE:
        k = sample == m
        lt[m], n = label_thirds(sub[k], lib[k], x[k], label[k], b12, b23)
        lt_decoy[m], _ = label_thirds(sub[k], lib[k], fits[m]['xs'], label[k], b12, b23)
        support[m] = n.min(1) >= MIN_SUPPORT
        zero[m] = core_zero(sub[k], x[k], b12, b23)
        boot_inputs[m] = {'x': x[k], 'lib': lib[k], 'y': sub[k][:, np.flatnonzero(hk)].toarray(), 'genes': names[gi][hk]}
    support_ok = np.all([support[m] for m in MICE], 0)
    rows, store = [], {}
    for j, g in enumerate(names[gi]):
        store[g] = {m: (fits[m]['curve'][j], fits[m]['decoy'][j], fits[m]['clusters'][j], fits[m]['bulk'][j],
                        fits[m]['bins'][j], fits[m]['bin_x']) for m in MICE}
        row = {'gene': g, 'b12': b12, 'b23': b23, 'universe': bool(universe[gi[j]]),
               'neighbour_ok': bool(neighbour_ok[gi[j]]), 'neighbour_ratio_control': ratio['control'][gi[j]],
               'neighbour_ratio_IR': ratio['IR'][gi[j]],
               'converged': bool(np.all([fits[m]['converged'][j] for m in MICE])),
               **{f'support_S{s + 1}': bool(support_ok[s]) for s in range(3)}}
        for m in MICE:
            row[f'bulk_{m}'] = fits[m]['bulk'][j]
            row.update({f'cluster_S{s + 1}_{m}': fits[m]['clusters'][j, s] for s in range(3)})
            row.update({f'label_change_S{s + 1}_{m}': lt[m][j, s, 1] - lt[m][j, s, 0] for s in range(3)})
            row.update({f'zero_third_S{s + 1}_{m}': bool(zero[m][j, s]) for s in range(3)})
            row.update({f'label_change_decoy_S{s + 1}_{m}': lt_decoy[m][j, s, 1] - lt_decoy[m][j, s, 0]
                        for s in range(3)})
        rows.append(row)
    print(f'{len(gi)} genes  b12 {b12:.3f} b23 {b23:.3f}', flush=True)

    df = pd.DataFrame(rows).set_index('gene')
    genes = df.index.to_numpy()
    curve = {m: np.stack([store[g][m][0] for g in genes]) for m in MICE}
    decoy = {m: np.stack([store[g][m][1] for g in genes]) for m in MICE}
    W = {m: np.stack([within_core(curve[m][i], df.b12.iloc[i], df.b23.iloc[i]) for i in range(len(genes))]) for m in MICE}
    Wd = {m: np.stack([within_core(decoy[m][i], df.b12.iloc[i], df.b23.iloc[i]) for i in range(len(genes))]) for m in MICE}
    L = {m: df[[f'label_change_S{s + 1}_{m}' for s in range(3)]].to_numpy() for m in MICE}
    Ld = {m: df[[f'label_change_decoy_S{s + 1}_{m}' for s in range(3)]].to_numpy() for m in MICE}
    support_ok = df[[f'support_S{s + 1}' for s in range(3)]].to_numpy()
    screened = (df.universe & df.neighbour_ok & df.converged).to_numpy()

    calls = {split: category_a(W, L, support_ok, split) & screened[:, None] for split in SPLITS}
    decoy_calls = category_a(Wd, Ld, support_ok, 'condition') & screened[:, None]
    for s in range(3):
        df[f'catA_S{s + 1}'] = calls['condition'][:, s]
        df[f'W_condition_S{s + 1}'] = split_value(W, 'condition')[:, s]
        df[f'W_label_condition_S{s + 1}'] = split_value(L, 'condition')[:, s]
        for split in ('relabeling 1', 'relabeling 2'):
            df[f'W_{split}_S{s + 1}'] = split_value(W, split)[:, s]
        pw = split_pairs(W, 'condition')[:, :, s]
        df[f'W_min_abs_pair_S{s + 1}'] = np.abs(pw).min(0)
        df[f'segment_view_S{s + 1}'] = split_value({m: df[f'cluster_S{s + 1}_{m}'].to_numpy() for m in MICE}, 'condition')
    df['catA'] = calls['condition'].any(1)
    for m in MICE:
        for s in range(3):
            df[f'W_S{s + 1}_{m}'] = W[m][:, s]
    unsupported = np.stack([df[[f'zero_third_S{s + 1}_{m}' for m in MICE]].any(axis=1).to_numpy() for s in range(3)], 1)
    for s in range(3):
        df[f'unsupported_S{s + 1}'] = unsupported[:, s]
    Wn = {m: np.where(unsupported, np.nan, W[m]) for m in MICE}
    n_real, n_decoy = int(calls['condition'].sum()), int(decoy_calls.sum())
    false_share = n_decoy / max(n_real, 1)
    relabel_share = np.mean([calls[s].sum() for s in ('relabeling 1', 'relabeling 2')]) / max(n_real, 1)

    # display map: |condition response| >= 1 somewhere in a core, all four pairs agreeing in sign there
    delta = split_value(curve, 'condition')
    dpairs = split_pairs(curve, 'condition')
    in_core = np.zeros((len(genes), len(GRID)), bool)
    for i in range(len(genes)):
        for lo, hi in cores(df.b12.iloc[i], df.b23.iloc[i]):
            in_core[i] |= (GRID >= lo) & (GRID <= hi)
    agree = (np.sign(dpairs) == np.sign(delta)[None]).all(0)
    df['in_map'] = screened & ((np.abs(delta) >= CHANGE_LOG2) & agree & in_core).any(1)

    # ---------------------------------------------------------------------------------------------- handoffs
    def xstar(cv, xr, amp_rule=True):
        inr = [np.where((GRID >= xr[0]) & (GRID <= xr[1]), c, np.nan) for c in cv]
        if amp_rule and min(float(np.nanmax(c) - np.nanmin(c)) for c in inr) < AMP_LOG2:
            return np.nan
        e, l = (scaled_profile(c) for c in inr)
        return crossing(e, l, GRID)

    # the 2.5-97.5 % range of x in each mouse
    xrange_ = {m: tuple(np.quantile(x[sample == m], [0.025, 0.975])) for m in MICE}

    def pair_positions(get_curve, amp_rule=True):
        out = np.full((len(handoff_pairs), len(MICE)), np.nan)
        for i, (e, l) in enumerate(zip(handoff_pairs.early, handoff_pairs.late)):
            if e not in store or l not in store:
                continue
            for j, m in enumerate(MICE):
                out[i, j] = xstar((get_curve(e, m), get_curve(l, m)), xrange_[m], amp_rule)
        return out

    xs_obs = pair_positions(lambda g, m: store[g][m][0])
    xs_noamp = pair_positions(lambda g, m: store[g][m][0], amp_rule=False)
    # bootstrap: resample units within each mouse, refit the handoff genes' curves with COAST (all mice together)
    brng = np.random.default_rng(6)
    all_draws = [{m: brng.integers(0, 1 << 31) for m in MICE} for _ in range(N_BOOT)]   # same draws as the serial loop

    def one_boot(draws):
        per = boot_inputs
        idx = {m: np.random.default_rng(draws[m]).integers(0, len(d['x']), len(d['x'])) for m, d in per.items()}
        cat = lambda key: np.concatenate([per[m][key][idx[m]] for m in per])  # noqa: E731
        sm = np.concatenate([np.full(len(idx[m]), m) for m in per])
        genes0 = per[MICE[0]]['genes']
        cv = coast_curves(cat('y'), cat('lib'), cat('x'), sm, genes0, 1)
        return pair_positions(lambda g, m: cv[m][list(genes0).index(g)])

    from joblib import Parallel, delayed
    boot = np.stack(Parallel(n_jobs=args.jobs, verbose=5)(delayed(one_boot)(d) for d in all_draws))

    hp = handoff_pairs.copy()
    for j, m in enumerate(MICE):
        hp[f'x_{m}'] = xs_obs[:, j]
        hp[f'x_noamp_{m}'] = xs_noamp[:, j]
        hp[f'x_lo_{m}'] = np.nanpercentile(boot[:, :, j], 2.5, 0)
        hp[f'x_hi_{m}'] = np.nanpercentile(boot[:, :, j], 97.5, 0)
        hp[f'boot_present_{m}'] = np.isfinite(boot[:, :, j]).mean(0)
    q = {m: xs_obs[:, j] for j, m in enumerate(MICE)}
    hp['eligible'] = np.isfinite(q['Ctrl1A2']) & np.isfinite(q['Ctrl1A4'])
    hp['shift'] = split_value(q, 'condition')
    pr = split_pairs(q, 'condition')
    hp['pairs_agree'] = (np.sign(pr) == np.sign(hp['shift'].to_numpy())[None]).all(0)
    for split in ('relabeling 1', 'relabeling 2'):
        hp[f'shift_{split}'] = split_value(q, split)
    hp['specific'] = (hp['shift_relabeling 1'].abs() <= SPECIFIC * hp['shift'].abs()) & \
                     (hp['shift_relabeling 2'].abs() <= SPECIFIC * hp['shift'].abs())
    bshift = split_value({m: boot[:, :, j] for j, m in enumerate(MICE)}, 'condition')
    hp['shift_lo'] = np.nanpercentile(bshift, 2.5, 0)
    hp['shift_hi'] = np.nanpercentile(bshift, 97.5, 0)
    hp['shifted'] = hp.eligible & hp.pairs_agree & (hp['shift'].abs() >= SHIFT_MIN) & hp.specific & \
                    ((hp.shift_lo > 0) | (hp.shift_hi < 0))
    hp['lost'] = hp.eligible & ~np.isfinite(q['IR2A2']) & ~np.isfinite(q['IR2A4'])
    ctrl_x = np.nanmean([q[m] for m in CONTROLS], 0)
    for role in ('early', 'late'):
        lv = []
        for g, cx in zip(hp[role], ctrl_x):
            if g not in store or not np.isfinite(cx):
                lv.append(np.nan)
                continue
            w = (GRID >= cx - 0.1) & (GRID <= cx + 0.1)
            lv.append(split_value({m: np.nanmean(store[g][m][0][w]) for m in MICE}, 'condition'))
        hp[f'level_{role}'] = lv
    hp.to_csv(out / 'handoffs.csv', index=False)
    np.save(out / 'handoff_bootstrap.npy', boot)
    if args.handoffs_only:
        print(hp[['early', 'late', 'shift', 'shifted', 'lost']].to_string())
        return

    # ---------------------------------------------------------------------------------------------- programs, sets
    sets = json.loads((root / 'paper_figures/gene_sets.json').read_text())
    tr = pd.read_csv(REPO / 'inputs/programs_transporters.csv')
    markers = pd.read_csv(REPO / 'inputs/injury_markers.csv', index_col=0).index.tolist()
    programs = {'T_PT': tr.loc[tr.in_T_PT.astype(bool), 'mouse'].tolist(),
                'C': sorted(set(sets['MSigDB_Hallmark_2020::G2-M Checkpoint']) | set(sets['MSigDB_Hallmark_2020::E2F Targets'])),
                'R': markers}
    in_screen = pd.Series(screened, index=genes)
    prog_rows, prog_profiles = [], {}
    for name, mem in programs.items():
        idx = np.flatnonzero(np.isin(genes, mem) & in_screen.to_numpy())
        for split in SPLITS:
            prof = split_value({m: curve[m][idx] for m in MICE}, split).mean(0)
            prog_profiles[f'{name}|{split}'] = prof
        for k, (a, b) in enumerate((a, b) for a in INJURED for b in CONTROLS):
            prog_profiles[f'{name}|{a}−{b}'] = (curve[a][idx] - curve[b][idx]).mean(0)
        seg = split_value({m: df.iloc[idx][[f'cluster_S{s + 1}_{m}' for s in range(3)]].to_numpy() for m in MICE},
                          'condition').mean(0)
        prog_profiles[f'{name}|segment_view'] = seg
        wc = np.nanmean(split_value(Wn, 'condition')[idx], 0)
        prog_rows.append({'program': name, 'members_used': len(idx), **{f'segment_view_S{s + 1}': seg[s] for s in range(3)},
                          **{f'W_S{s + 1}': wc[s] for s in range(3)},
                          **{f'W_{sp}_S{s + 1}': np.nanmean(split_value(Wn, sp)[idx], 0)[s] for sp in ('relabeling 1', 'relabeling 2')
                             for s in range(3)}})
    pd.DataFrame(prog_rows).to_csv(out / 'programs.csv', index=False)

    uni = np.flatnonzero(screened)
    pos_of = {g: i for i, g in enumerate(genes[uni])}
    members = {}
    for name, mem in sets.items():
        idx = np.array([pos_of[g] for g in mem if g in pos_of], int)
        if len(idx) >= MIN_SET:
            members[name] = idx
    gene_w = {}
    for split in SPLITS:
        gene_w[split] = split_value(Wn, split)[uni]
        for k, pw in enumerate(split_pairs(Wn, split)):
            gene_w[f'{split}|{k}'] = pw[uni]
    sets_df = set_screen(gene_w, members, np.random.default_rng(66))
    sets_df.to_csv(out / 'pathways.csv', index=False)
    n_set_calls = {s: int(sets_df[(sets_df.split == s)].call.sum()) for s in SPLITS}
    np.savez_compressed(out / 'all_curves.npz', grid=GRID, genes=genes,
                        **{f'curve|{m}': curve[m].astype(np.float32) for m in MICE})
    set_share = np.mean([n_set_calls['relabeling 1'], n_set_calls['relabeling 2']]) / max(n_set_calls['condition'], 1)

    # ---------------------------------------------------------------------------------------------- save
    df.to_csv(out / 'genes.csv')
    pd.DataFrame([axis_row]).to_csv(out / 'axes.csv', index=False)
    keep = df.index[df.catA | df.in_map | df.index.isin(handoff_genes) |
                    df.index.isin(sum(programs.values(), []))].tolist()
    ki = [np.flatnonzero(genes == g)[0] for g in keep]
    np.savez_compressed(out / 'curves.npz', grid=GRID, genes=np.array(keep),
                        **{f'{part}|{m}': np.stack([store[g][m][i] for g in keep])
                           for m in MICE for i, part in enumerate(('curve', 'decoy', 'clusters', 'bulk', 'bins', 'bin_x'))},
                        **{f'program|{k}': v for k, v in prog_profiles.items()})
    summary = {'amp_log2': AMP_LOG2, 'n_units': {m: int((sample == m).sum()) for m in MICE}, 'n_screened': int(screened.sum()),
               'n_neighbour_dropped': int((df.universe & ~df.neighbour_ok).sum()),
               'category_A': {'calls': n_real, 'genes': int(df.catA.sum()),
                              'by_segment': {f'S{s + 1}': int(calls['condition'][:, s].sum()) for s in range(3)},
                              'up': int((calls['condition'] & (split_value(W, 'condition') > 0)).sum()),
                              'decoy_calls': n_decoy, 'false_share': false_share,
                              'relabeling_calls': {s: int(calls[s].sum()) for s in ('relabeling 1', 'relabeling 2')},
                              'relabeling_share': relabel_share, 'calibrated': false_share <= MAX_FALSE_SHARE},
               'map_genes': int(df['in_map'].sum()),
               'handoffs': {'pairs': int(len(hp)), 'eligible': int(hp.eligible.sum()), 'shifted': int(hp.shifted.sum()),
                            'lost': int(hp.lost.sum()),
                            'shifted_pairs': hp.loc[hp.shifted, ['early', 'late', 'shift']].round(3).values.tolist(),
                            'lost_pairs': hp.loc[hp.lost, ['early', 'late']].values.tolist()},
               'pathways': {'sets': len(members), 'calls': n_set_calls, 'calibration_share': set_share,
                            'calibrated': set_share <= MAX_FALSE_SHARE},
               'programs': pd.DataFrame(prog_rows).round(3).to_dict('records')}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == '__main__':
    main()
