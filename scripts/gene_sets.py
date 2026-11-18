"""Pathway gene sets for the paper's set screens (Figs. 5 and 6), built on the COAST fits.

Reactome 2022, MSigDB Hallmark 2020 and KEGG 2019 Mouse (<data-root>/pathway_gene_sets/, Enrichr JSON) mapped onto
mouse symbols through the shared 1:1 orthologs, kept to the genes measured in both COAST fits, sets with 10-300 such
members.

  python scripts/gene_sets.py [--data-root <dir>] [--results-root <dir>]

Writes <results-root>/paper_figures/gene_sets.json ({library::pathway: members}).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
SET_SIZES = (10, 300)
OUT = 'paper_figures/gene_sets.json'


def main(argv=None):
    import h5py
    from fig3_common import RUNS

    from coast_paper import layout
    from coast_paper.pathways import pathway_sets

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-root', default=str(REPO / 'data'))
    p.add_argument('--results-root', default=str(REPO / 'results'))
    args = p.parse_args(argv)
    root = Path(args.results_root)
    measured = None
    for run in ('aki', 'hvm'):
        with h5py.File(root / RUNS[run] / '02_qc/units_qc.h5ad', 'r') as h:
            names = set(h['var']['_index'][:].astype(str))
        measured = names if measured is None else measured & names
    measured = sorted(measured)
    sets = pathway_sets(Path(args.data_root) / 'pathway_gene_sets', measured, layout.orthologs(args.data_root), SET_SIZES)
    (root / OUT).parent.mkdir(parents=True, exist_ok=True)
    (root / OUT).write_text(json.dumps(sets))
    print(f'{len(sets)} sets on {len(measured)} measured genes ->', root / OUT)


if __name__ == '__main__':
    main()
