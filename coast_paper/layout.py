"""Where the scripts find their inputs. Every script takes ``--data-root`` (default ``data/``) and ``--results-root``
(default ``results/``); neither is part of this repository.

data/
  <section>/square_002um/      Space Ranger output of the Visium HD run at 2 um (binned_outputs/square_002um)
  <section>.geojson            segmentation of the section's H&E, one polygon per tubule cross-section
  <section>.tif                full-resolution H&E image (Figs. 1-3)
  orthologs.csv                HCOP human-mouse orthologs (columns human_symbol, mouse_symbol)
  pathway_gene_sets/           Enrichr libraries Reactome_2022, MSigDB_Hallmark_2020, KEGG_2019_Mouse (.json)
  cells/                       bin2cell cells of the mouse sections (Fig. 4c)
  segmentation_reference/      manual outlines of the held-out Ctrl1A2 patch (Fig. 2)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# the two fits of the paper: section -> condition
RUNS = {'aki': {'Ctrl1A2': 'Control', 'Ctrl1A4': 'Control', 'IR2A2': 'IR', 'IR2A4': 'IR'},
        'hvm': {'Ctrl1A2': 'Mouse', 'Ctrl1A4': 'Mouse', 'HUK1_COR1': 'Human', 'HUK1_MED1': 'Human'}}
SECTIONS = ['Ctrl1A2', 'Ctrl1A4', 'IR2A2', 'IR2A4', 'HUK1_COR1', 'HUK1_MED1']


def bins(data_root, section) -> Path:
    return Path(data_root) / section / 'square_002um'


def segmentation(data_root, section) -> Path:
    return Path(data_root) / f'{section}.geojson'


def he(data_root, section) -> Path:
    return Path(data_root) / f'{section}.tif'


def orthologs(data_root) -> pd.DataFrame:
    """The shared 1:1 orthologs: pairs whose symbols each occur once in the table and are measured in both species
    (human: HUK1_COR1, mouse: Ctrl1A2), in the gene order of the mouse matrix."""
    import coast

    mouse = coast.io.visium_hd_genes(bins(data_root, 'Ctrl1A2'))
    human = coast.io.visium_hd_genes(bins(data_root, 'HUK1_COR1'))
    o = pd.read_csv(Path(data_root) / 'orthologs.csv')[['human_symbol', 'mouse_symbol']]
    o = o[~o['human_symbol'].duplicated(keep=False) & ~o['mouse_symbol'].duplicated(keep=False)]
    o = o[o['human_symbol'].isin(human) & o['mouse_symbol'].isin(mouse)]
    return o.iloc[mouse.get_indexer(o['mouse_symbol']).argsort()].reset_index(drop=True)


def marker_panels() -> dict:
    """Marker panels, labels and QC regions of the mouse kidney (marker_panels.yaml), shared by both fits."""
    import yaml

    return yaml.safe_load((Path(__file__).with_name('marker_panels.yaml')).read_text())
