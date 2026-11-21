"""Pathway gene sets of the set screens (Figs. 5 and 6)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# Enrichr libraries, one JSON file each ({pathway: [gene symbols]}), in data/pathway_gene_sets/
LIBRARIES = ('Reactome_2022', 'MSigDB_Hallmark_2020', 'KEGG_2019_Mouse')


def pathway_sets(folder, measured, orthologs: pd.DataFrame, sizes=(10, 300)) -> dict:
    """{library::pathway: members}: each set's symbols mapped onto ``measured`` (mouse symbols), directly or through
    the 1:1 ``orthologs`` (human_symbol -> mouse_symbol); kept when ``sizes[0]``-``sizes[1]`` members are measured.
    Within a library, sets are listed by their number of measured members, largest first."""
    lookup = {str(g).upper(): str(g) for g in measured}
    translate = {}
    for human, mouse in zip(orthologs['human_symbol'].astype(str), orthologs['mouse_symbol'].astype(str)):
        translate.setdefault(human.upper(), mouse)
    out = {}
    for library in LIBRARIES:
        rows = []
        for pathway, members in json.loads((Path(folder) / f'{library}.json').read_text()).items():
            hit = set()
            for symbol in {str(g).upper() for g in members}:
                if symbol in lookup:
                    hit.add(symbol)
                elif translate.get(symbol, '').upper() in lookup:
                    hit.add(translate[symbol].upper())
            rows.append({'pathway': str(pathway), 'n': len(hit), 'retained': len(hit) >= 1,
                         'genes': sorted(lookup[s] for s in hit)})
        table = pd.DataFrame(rows).sort_values(['retained', 'n'], ascending=[False, False]).reset_index(drop=True)
        table = table[table['n'].between(sizes[0], min(sizes[1], len(measured) - 1))]
        out.update({f'{library}::{r.pathway}': list(r.genes) for r in table.itertuples()})
    return out
