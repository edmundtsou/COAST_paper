"""The paper's two fits built with COAST (github.com/edmundtsou/COAST), in the run layout the figure scripts read, plus
`two_pass` for the reruns of Fig. 3d (robustness) and Fig. 6 (injury-blind axis).

  python scripts/coast_fit.py --run aki      # control vs AKI mouse
  python scripts/coast_fit.py --run hvm      # control mouse vs human, on shared 1:1 orthologs

Steps (marker panels, labels and QC regions: coast_paper/marker_panels.yaml):
  units      coast.io.read_visium_hd + read_segmentation, coast.pp.bins_to_units: every 2 um bin goes to the polygon
             covering its centre; hvm bins are first cut to the shared 1:1 orthologs, in mouse symbols
  QC         coast.pp.filter_units (>= 500 counts, bin coverage >= 0.9, MAD 3 per sample x segmentation class on log
             counts, log counts per bin and the complexity residual) and coast.pp.doublets (tiers 2, 3, 4 discard;
             glomeruli exempt; regions and adjacency of qc_regions)
  pass 1     coast.pp.filter_genes (5 % of units, 20 counts, panel genes kept), normalize, integrate (Harmony on
             sample, variable genes in every condition), Leiden (resolution 2), coast.tl.label_clusters
  pass 2     the nephron tubule labels only (drop_classes, rejected and Unassigned removed), the same steps again
  curve      coast.tl.pseudostructure on the 50 Harmony dimensions, oriented by the axis_anchors (early -> late)

Writes <results-root>/coast_runs/<run>/: 01_units/<section>_bin_to_unit.parquet (the unit of every assigned bin),
02_qc/{units_qc.h5ad, qc_flags.parquet}, 03_integration/{pass1_labelled,pass2}.h5ad and cluster scores,
04_pseudospace/{pseudospace.parquet, curve_nodes.npz, order_metrics.csv, manifest.json}.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from coast_paper import layout  # noqa: E402

OUT = 'coast_runs'
SEED = 0


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--run', choices=sorted(layout.RUNS), required=True)
    p.add_argument('--data-root', default=str(REPO / 'data'))
    p.add_argument('--results-root', default=str(REPO / 'results'))
    return p.parse_args(argv)


def panels(run: str = '') -> dict:
    """The marker panels (the same for both fits)."""
    return layout.marker_panels()


def protected_genes(P: dict) -> list:
    return sorted({g for gs in P['label_panels'].values() for g in gs} | set(P['axis_anchors']['early'])
                  | set(P['axis_anchors']['late']) | set(P.get('extra_marker_genes', []))
                  | set(P.get('extra_protected_genes', [])) | {g for gs in P['qc_regions']['markers'].values() for g in gs})


def exclude_regex(genes=()) -> str:
    """COAST's default mitochondrial / ribosomal exclusion plus a list of gene names withdrawn from the features."""
    import coast

    if not len(genes):
        return coast.pp.DEFAULT_EXCLUDE
    return coast.pp.DEFAULT_EXCLUDE + '|^(?:' + '|'.join(map(re.escape, sorted(genes))) + ')$'


# ------------------------------------------------------------------------------------------------- units and QC
def load_units(run: str, data_root: Path, P: dict, out: Path):
    """Bins -> units for every section of the run. Returns the units (raw counts), the assigned bins x QC region
    markers (for the doublet calls) and each unit's polygon; writes each section's bin -> unit table to ``out``."""
    import anndata as ad
    import coast

    orthologs = layout.orthologs(data_root) if run == 'hvm' else None
    markers = sorted({g for gs in P['qc_regions']['markers'].values() for g in gs})
    out.mkdir(parents=True, exist_ok=True)
    units, bins, polygons = {}, [], []
    for sample, group in layout.RUNS[run].items():
        section = coast.io.read_visium_hd(layout.bins(data_root, sample))
        if orthologs is not None:   # one gene space: the shared 1:1 orthologs, named by their mouse symbol
            section = section[:, orthologs['human_symbol' if group == 'Human' else 'mouse_symbol'].to_numpy()].copy()
            section.var_names = orthologs['mouse_symbol'].to_numpy()
        segmentation = coast.io.read_segmentation(layout.segmentation(data_root, sample))
        units[sample] = coast.pp.bins_to_units(section, segmentation, sample)
        units[sample].obs['condition'] = group
        inside = section.obs['unit'].notna().to_numpy()
        pd.DataFrame({'bin_id': section.obs_names[inside], 'unit': section.obs['unit'][inside].to_numpy()}).to_parquet(
            out / f'{sample}_bin_to_unit.parquet')
        bins.append(section[inside, [g for g in markers if g in section.var_names]].copy())
        polygons.append(pd.Series(segmentation['geometry'].to_numpy(), index=units[sample].obs_names))
        del section
    adata = ad.concat(units, merge='same')
    adata.obs['sample'] = pd.Categorical(adata.obs['sample'], categories=list(layout.RUNS[run]))
    adata.obs['condition'] = adata.obs['condition'].astype('category')
    return adata, ad.concat(bins, join='outer', fill_value=0), pd.concat(polygons)


def quality_control(adata, bins, polygons: pd.Series, P: dict):
    import coast

    floors = coast.pp.filter_units(adata, min_counts=500, min_coverage=0.9, n_mads=None)
    regions, adjacency = P['qc_regions']['markers'], P['qc_regions']['adjacency']
    coast.pp.doublets(floors, bins[bins.obs['unit'].isin(floors.obs_names)], polygons[floors.obs_names].tolist(),
                      regions, adjacency, class_key='seg_class', exempt=('glomerulus',), discard=('2', '3', '4'),
                      seed=SEED)
    mad = coast.pp.filter_units(floors, min_counts=500, min_coverage=0.9, n_mads=3.0,
                                groupby=['sample', 'seg_class'], bins_key='n_spots', min_group_size=50)
    keep = floors.obs_names.isin(mad.obs_names) & ~floors.obs['doublet'].to_numpy(bool)
    flags = floors.obs[['sample', 'seg_class', 'doublet', *[c for c in floors.obs if c.startswith('doublet_tier')]]].copy()
    flags['mad_outlier'] = ~floors.obs_names.isin(mad.obs_names)
    flags['qc_retained'] = keep
    qc = floors[keep].copy()
    counts = {'polygons': adata.obs['sample'].value_counts(sort=False),
              'with bins': adata.obs.loc[adata.obs['n_spots'] > 0, 'sample'].value_counts(sort=False),
              'hard floors': floors.obs['sample'].value_counts(sort=False),
              'MAD retained': mad.obs['sample'].value_counts(sort=False),
              'doublets': floors.obs.loc[floors.obs['doublet'], 'sample'].value_counts(sort=False),
              'after QC': qc.obs['sample'].value_counts(sort=False)}
    coast.pp.normalize(qc)
    qc.layers['lognorm'] = qc.X.copy()
    qc.var['mt'] = qc.var_names.str.match(r'^(?:mt-|MT-)')
    qc.var['ribo'] = qc.var_names.str.match(r'^(?:Rp[ls]\d|RP[LS]\d|Mrp[ls]\d|MRP[LS]\d)')
    qc.var['exclude_from_harmony_hvg'] = qc.var_names.str.contains(coast.pp.DEFAULT_EXCLUDE)
    qc.obs['qc_retained'] = True
    return qc, pd.DataFrame(counts).fillna(0).astype(int), flags


# ------------------------------------------------------------------------------------------- two passes and curve
def _pass(units, P: dict, group_key: str, exclude: str, key: str):
    """filter_genes -> normalize -> integrate -> Leiden on QC units (raw counts in layers['counts'])."""
    import coast
    import scanpy as sc

    a = coast.pp.filter_genes(units, keep=protected_genes(P))
    coast.pp.normalize(a)
    coast.pp.integrate(a, batch_key='sample', group_key=group_key, exclude=exclude, random_state=SEED)
    sc.tl.leiden(a, resolution=2, flavor='igraph', n_iterations=2, random_state=SEED, key_added=key)
    return a


def two_pass(qc, P: dict, exclude_genes=(), pre_umap: bool = False):
    """Both passes on QC units. Returns (pass 1, pass 2 with obs['pseudostructure'], cluster score table)."""
    import coast
    import scanpy as sc

    exclude = exclude_regex(exclude_genes)
    units = qc.copy()
    units.X = units.layers['counts'].copy()
    p1 = _pass(units, P, 'condition', exclude, 'leiden_coarse')
    if pre_umap:   # Fig. 1: the same units before Harmony
        pre = sc.AnnData(obs=p1.obs[[]], obsm={'X_pca': p1.obsm['X_pca']})
        sc.pp.neighbors(pre, use_rep='X_pca', n_neighbors=25, transformer='sklearn', random_state=SEED)
        sc.tl.umap(pre, min_dist=0.3, random_state=SEED)
        p1.obsm['X_umap_pre_harmony'] = pre.obsm['X_umap']
    scores = coast.tl.label_clusters(p1, P['label_panels'], cluster_key='leiden_coarse', key_added='segment_class')
    rejected = P.get('rejected_labels', {})
    family = P['label_to_family']
    label = p1.obs['segment_class'].astype(str).replace(rejected)
    p1.obs['segment_class'] = label.astype('category')
    p1.obs['coarse_class'] = label.map(lambda l: family.get(l, l)).astype('category')
    p1.obs['broad_tubule_marker_call'] = p1.obs['coarse_class']
    drop = set(P['drop_classes']) | set(rejected.values()) | {'Unassigned'}
    tubule = ~p1.obs['coarse_class'].astype(str).isin(drop) & ~label.isin(drop)
    p2 = _pass(units[tubule.to_numpy()].copy(), P, 'condition', exclude, 'leiden_pass2')
    for col in ('segment_class', 'coarse_class', 'broad_tubule_marker_call', 'leiden_coarse'):
        p2.obs[col] = p1.obs.loc[p2.obs_names, col].astype(str).astype('category')
    coast.tl.pseudostructure(p2, early_genes=P['axis_anchors']['early'], late_genes=P['axis_anchors']['late'],
                             seed=SEED)
    return p1, p2, scores


def order_metrics(table: pd.DataFrame, order: list) -> pd.DataFrame:
    """Spearman rho of the coordinate against the label's place in `order`, and inverted adjacent label medians."""
    from scipy.stats import spearmanr

    rows = []
    for name, part in [('all', table)] + [(c, g) for c, g in table.groupby('condition', observed=True)]:
        rank = part['segment_class'].map({l: i for i, l in enumerate(order)})
        ok = rank.notna()
        med = part[ok].groupby('segment_class', observed=True)['pseudospace'].median().reindex(order).dropna()
        rows.append({'coordinate': 'pseudospace', 'units': name, 'n_units': int(len(part)),
                     'segment_order_rho': float(spearmanr(med.index.map({l: i for i, l in enumerate(order)}),
                                                          med.to_numpy()).statistic),
                     'n_inversions': int((np.diff(med.to_numpy()) < 0).sum()),
                     'unit_rank_rho': float(spearmanr(rank[ok], part.loc[ok, 'pseudospace']).statistic)})
    return pd.DataFrame(rows)


def stage04_table(p2) -> pd.DataFrame:
    t = pd.DataFrame({'sample': p2.obs['sample'].astype(str), 'condition': p2.obs['condition'].astype(str),
                      'segment_class': p2.obs['segment_class'].astype(str),
                      'coarse_class': p2.obs['coarse_class'].astype(str),
                      'pseudospace': p2.obs['pseudostructure'].astype(float)}, index=p2.obs_names.copy())
    t.index.name = 'obs_name'
    return t


def write_stage04(p2, P: dict, folder: Path, extra: dict | None = None) -> pd.DataFrame:
    folder.mkdir(parents=True, exist_ok=True)
    table = stage04_table(p2)
    table.to_parquet(folder / 'pseudospace.parquet')
    np.savez(folder / 'curve_nodes.npz', nodes=p2.uns['coast']['nodes'],
             pseudospace=p2.uns['coast']['node_pseudostructure'])
    order_metrics(table, P['segment_order']).to_csv(folder / 'order_metrics.csv', index=False)
    root = table['pseudospace'].idxmin()
    (folder / 'manifest.json').write_text(json.dumps({'stage': '04', 'method': 'COAST', 'summary': {
        'n_units': int(len(table)), 'root_unit': str(root), 'root_rule': 'unit at pseudostructure 0',
        'n_nodes': int(len(p2.uns['coast']['nodes'])), **(extra or {})}}, indent=1))
    return table


def h5_safe(a):
    """Drop what h5ad cannot store (graph params with None values are fine; uns objects from COAST are arrays)."""
    a.uns.pop('coast', None)
    return a


def build(args) -> None:
    import coast

    t0 = time.time()
    run, results_root, data_root = args.run, Path(args.results_root), Path(args.data_root)
    out = results_root / OUT / run
    for stage in ('02_qc', '03_integration', '04_pseudospace'):
        (out / stage).mkdir(parents=True, exist_ok=True)
    P = panels(run)
    adata, bins, polygons = load_units(run, data_root, P, out / '01_units')
    qc, counts, flags = quality_control(adata, bins, polygons, P)
    flags.to_parquet(out / '02_qc' / 'qc_flags.parquet')   # the hard-floor units: doublet tiers, MAD, retained
    print(counts.to_string())
    qc.write_h5ad(out / '02_qc' / 'units_qc.h5ad')
    p1, p2, scores = two_pass(qc, P, pre_umap=True)
    scores.to_csv(out / '03_integration' / 'pass1_cluster_scores.csv')
    nodes = dict(p2.uns['coast'])
    h5_safe(p1).write_h5ad(out / '03_integration' / 'pass1_labelled.h5ad')
    table = write_stage04(p2, P, out / '04_pseudospace')
    p2.uns['coast'] = nodes
    h5_safe(p2).write_h5ad(out / '03_integration' / 'pass2.h5ad')
    counts['pass 2 (curve)'] = table['sample'].value_counts().reindex(counts.index).fillna(0).astype(int)
    pt = table[table['coarse_class'] == 'PT']
    for seg in ('PT-S1', 'PT-S2', 'PT-S3'):
        counts[seg] = pt[pt['segment_class'] == seg]['sample'].value_counts().reindex(counts.index).fillna(0).astype(int)
    counts.loc['total'] = counts.sum()
    counts.to_csv(out / 'stage_counts.csv')
    (out / 'record.json').write_text(json.dumps({
        'coast_version': coast.__version__, 'coast_path': str(Path(coast.__file__).parent),
        'run': run, 'seconds': round(time.time() - t0),
        'pt_medians': pt.groupby('segment_class')['pseudospace'].median().round(4).to_dict()}, indent=1))
    print(counts.to_string())
    print(pt.groupby('segment_class')['pseudospace'].median().round(4).to_dict(), f'{time.time() - t0:.0f} s')


if __name__ == '__main__':
    build(parse_args())
