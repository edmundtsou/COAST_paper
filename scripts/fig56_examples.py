"""Example genes and sets of Figs. 5 and 6, chosen from the current shape_clusters.py output by the rules the figure
scripts state, so a rerun can never show a gene or set that is no longer called:
 d  one transporter (Slc / Abc genes) from each gene shape cluster, in cluster order: the earlier choice where it is
    still in that cluster, otherwise the cluster's transporter with the largest change (rms of the difference curve)
 f  two genes named on each cluster: the earlier names still in that cluster, filled with its largest changes
 g  per pathway group, the called set with the smallest competitive p, skipping broad Hallmarks with no PT meaning
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

TRANSPORTER = r'^(?:Slc|Abc)'
BROAD = {'MSigDB_Hallmark_2020::Adipogenesis'}


def pick(shape_dir: Path, genes_d: list, examples: dict, highlight: list):
    g = pd.read_csv(shape_dir / 'genes.csv').set_index('gene')
    g = g[g.changed]
    pw = pd.read_csv(shape_dir / 'pathways.csv').set_index('set')
    pw = pw[pw.changed]
    clusters = sorted(g.cluster.dropna().astype(int).unique())
    d, f = [], {}
    for c in clusters:
        members = g[g.cluster == c].sort_values('rms_condition', ascending=False)
        kept = [x for x in genes_d if x in members.index]
        tr = members[members.index.str.contains(TRANSPORTER)]
        d.append(kept[0] if kept else (tr.index[0] if len(tr) else members.index[0]))
        named = [x for x in sum(examples.values(), []) if x in members.index][:2]
        f[c] = (named + [x for x in members.index if x not in named])[:2]
    hl = []
    for grp, part in pw.groupby('group'):
        part = part.sort_values('p')
        prefer = [s for s in highlight if s in part.index]
        hl.append(prefer[0] if prefer else next(s for s in part.index if s not in BROAD))
    return d, f, hl
