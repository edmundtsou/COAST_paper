"""Every number quoted in the Fig. 5 and Fig. 6 Results, recomputed from the pipeline outputs, so the text can be checked
against (and rebuilt from) the code on GitHub.

Sources: <results-root>/paper_figures/fig{5,6}/screen (fig5_screen.py, fig6_screen.py: COAST curves, cluster means, end
and within-segment contrasts), fig{5,6}/shape_clusters (shape_clusters.py), fig6/screen/interpret_retention.csv
(fig6_interpret.py) and fig6/placement (fig6_placement.py). Peaks and extents are read from each section's COAST curve
over its defined range (COAST's 5th-95th percentile); a range "a-b" is the two sections of one group.

  python scripts/paper_numbers.py [--results-root <dir>]

Writes <results-root>/paper_figures/paper_numbers.md and prints it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
MOUSE, HUMAN = ['Ctrl1A2', 'Ctrl1A4'], ['HUK1_COR1', 'HUK1_MED1']
CTRL, IR = ['Ctrl1A2', 'Ctrl1A4'], ['IR2A2', 'IR2A4']
GENES5 = {'peak': ['Slc5a2', 'Slc7a7', 'Slc25a15', 'Slc10a2', 'Slc22a12', 'Mme', 'Hpgd', 'Dcxr', 'Slc22a6', 'Slc22a8'],
          'half_max': ['Slc5a2', 'Slc2a2'], 'end_contrast': ['Mme', 'Hpgd', 'Slc17a3', 'Dcxr', 'Slc22a6']}
GENES6 = {'peak': ['Khk', 'Slc26a1', 'Hmox1', 'Tk1', 'Slc6a13', 'Slc22a2', 'Cyp4a14', 'Acadm', 'Havcr1', 'Cyp24a1',
                   'Slc6a8'],
          'segment_change': ['Havcr1'], 'within_s2': ['Cyp4a14', 'Agt', 'Cyp24a1']}


def span(v, fmt='{:.2f}'):
    v = [x for x in v if np.isfinite(x)]
    if not v:
        return 'n/a'
    lo, hi = min(v), max(v)
    return fmt.format(lo) if fmt.format(lo) == fmt.format(hi) else f'{fmt.format(lo)}-{fmt.format(hi)}'


def curves(screen):
    z = np.load(screen / 'all_curves.npz', allow_pickle=True)
    names = list(np.asarray(z['genes']).astype(str))
    return z['grid'], {k.split('|')[1]: z[k] for k in z.files if k.startswith('curve|')}, names


def peak(grid, c):
    return float(grid[np.nanargmax(c)]) if np.isfinite(c).any() else np.nan


def half_max_end(grid, c):
    """Last position where the curve (counts per 10k) is at least half its maximum."""
    r = 2.0 ** c
    ok = np.isfinite(r) & (r >= 0.5 * np.nanmax(r))
    return float(grid[np.flatnonzero(ok)[-1]]) if ok.any() else np.nan


def shape_section(root, fig, a, b):
    sc = root / 'paper_figures' / fig / 'shape_clusters'
    s = json.loads((sc / 'summary.json').read_text())
    g = pd.read_csv(sc / 'genes.csv').set_index('gene')
    pw = pd.read_csv(sc / 'pathways.csv').set_index('set')
    sh = np.load(sc / 'shapes.npz', allow_pickle=True)
    x, sg = sh['x'], list(np.asarray(sh['genes']).astype(str))
    lines = [f"- screened {s['n_screened']:,}; eligible (graded) {s['n_eligible']:,}; called "
             f"{s['genes_changed']['condition']:,} (swaps {s['genes_changed']['swap 1']}, {s['genes_changed']['swap 2']})",
             f"- gene classes {s['gene_clusters']}"]
    hit = g[g.changed]
    for c, part in hit.groupby('cluster'):
        idx = [sg.index(n) for n in part.index if n in sg]
        pa, pb = x[np.argmax(sh['mean_a'][idx].mean(0))], x[np.argmax(sh['mean_b'][idx].mean(0))]
        lines.append(f'  - class {c} ({len(part)} genes): mean shape peak {a} {pa:.2f}, {b} {pb:.2f}; '
                     f'members incl. {", ".join(part.sort_values("rms_condition", ascending=False).index[:6])}')
    lines += [f"- sets tested {s['n_sets_tested']}; changed {s['sets_changed']['condition']} (swaps "
              f"{s['sets_changed']['swap 1']}, {s['sets_changed']['swap 2']}); changed and q <= 0.05: "
              f"{s['sets_changed_and_q05']}"]
    ch = pw[pw.changed].sort_values('q')
    for gr, part in ch.groupby('group'):
        best = part.index[0]
        mem = [m for m in str(part.loc[best, 'genes']).split(';') if m in sg] if 'genes' in part else []
        idx = [sg.index(m) for m in mem]
        pk = (f'peak {a} {x[np.argmax(sh["mean_a"][idx].mean(0))]:.2f}, {b} {x[np.argmax(sh["mean_b"][idx].mean(0))]:.2f}'
              if idx else '')
        lines.append(f'  - set group {gr} ({len(part)} sets): strongest {best} (n {part.loc[best, "n"]}, '
                     f'q {part.loc[best, "q"]:.3g}) {pk}')
    return lines


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--results-root', default=str(REPO / 'results'))
    args = p.parse_args(argv)
    root = Path(args.results_root)
    out = ['# Numbers for the Fig. 5 and Fig. 6 Results (paper_numbers.py)', '', '## Fig. 5 (mouse vs human)']

    s5 = root / 'paper_figures/fig5/screen'
    grid, cv, names = curves(s5)
    g5 = pd.read_csv(s5 / 'genes.csv').set_index('gene')
    out += shape_section(root, 'fig5', 'mouse', 'human')
    for gene in GENES5['peak']:
        if gene in names:
            j = names.index(gene)
            out.append(f'- {gene} peak: mouse {span([peak(grid, cv[m][j]) for m in MOUSE])}, '
                       f'human {span([peak(grid, cv[m][j]) for m in HUMAN])}')
    for gene in GENES5['half_max']:
        if gene in names:
            j = names.index(gene)
            out.append(f'- {gene} above half max through: mouse {span([half_max_end(grid, cv[m][j]) for m in MOUSE])}, '
                       f'human {span([half_max_end(grid, cv[m][j]) for m in HUMAN])}')
    for gene in GENES5['end_contrast']:
        if gene in g5.index:
            out.append(f'- {gene} S3-core minus S1-core (log2): mouse '
                       f'{span([g5.loc[gene, f"E_{m}"] for m in MOUSE], "{:+.1f}")}, human '
                       f'{span([g5.loc[gene, f"E_{m}"] for m in HUMAN], "{:+.1f}")}')
        if gene in names:
            j = names.index(gene)
            fold = lambda c: 2.0 ** (np.nanmax(c) - np.nanmin(c))  # noqa: E731
            out.append(f'  - {gene} max/min fold along the PT: mouse {span([fold(cv[m][j]) for m in MOUSE], "{:.1f}")}, '
                       f'human {span([fold(cv[m][j]) for m in HUMAN], "{:.1f}")}')

    out += ['', '## Fig. 6 (control vs AKI)']
    s6 = root / 'paper_figures/fig6/screen'
    grid, cv, names = curves(s6)
    g6 = pd.read_csv(s6 / 'genes.csv').set_index('gene')
    out += shape_section(root, 'fig6', 'control', 'AKI')
    for gene in GENES6['peak']:
        if gene in names:
            j = names.index(gene)
            out.append(f'- {gene} peak: control {span([peak(grid, cv[m][j]) for m in CTRL])}, '
                       f'AKI {span([peak(grid, cv[m][j]) for m in IR])}')
    for gene in GENES6['segment_change']:
        if gene in g6.index:
            d = [np.mean([g6.loc[gene, f'cluster_S{s}_{m}'] for m in IR]) -
                 np.mean([g6.loc[gene, f'cluster_S{s}_{m}'] for m in CTRL]) for s in (1, 2, 3)]
            out.append(f'- {gene} AKI minus control, S1/S2/S3 cluster means (log2): ' + ', '.join(f'{v:.1f}' for v in d))
    w = [c for c in g6.columns if c.startswith('W_S2_')]
    for gene in GENES6['within_s2']:
        cols = {m: f'W_S2_{m}' for m in CTRL + IR}
        if gene in g6.index and all(c in g6.columns for c in cols.values()):
            out.append(f'- {gene} within S2 (log2): control {span([g6.loc[gene, cols[m]] for m in CTRL], "{:+.2f}")}, '
                       f'AKI {span([g6.loc[gene, cols[m]] for m in IR], "{:+.2f}")}')
    if not w:
        out.append('- (no within-segment columns in genes.csv)')
    ret = s6 / 'interpret_retention.csv'
    if ret.exists():
        r = pd.read_csv(ret)
        out.append(f'- retention table ({ret.name}): ' + r.round(2).to_string(index=False).replace('\n', ' | '))
    pl = root / 'paper_figures/fig6/placement/verdict.json'
    if pl.exists():
        out.append(f'- injury-blind axis ({pl.name}): ' + json.dumps(json.loads(pl.read_text()))[:600])
    text = '\n'.join(out) + '\n'
    (root / 'paper_figures/paper_numbers.md').write_text(text)
    print(text)


if __name__ == '__main__':
    main()
