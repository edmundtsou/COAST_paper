# COAST paper

Analysis and figure code of the COAST paper.

[COAST](https://github.com/edmundtsou/COAST) (**C**ontinuous **O**rdering of **A**natomical **S**tructures from
**T**ranscriptomics) is the method: it orders cross-sections of a repeated tissue structure along one continuous axis,
the **pseudostructure** coordinate, and asks how genes change along it. This repository holds everything the paper
built around the method: the two COAST fits on the kidney data, the gene and pathway screens along the proximal
tubule, and every figure. The segmentation model that outlines the tubules on the H&E will be added under
[`segmentation/`](segmentation/).

The data are Visium HD sections of two control and two injured (AKI) mouse kidneys and two sections of one healthy
human kidney cortex. Two fits are made:

| Fit | Sections | Figures |
|---|---|---|
| `aki` | Ctrl1A2, Ctrl1A4 (control); IR2A2, IR2A4 (ischaemia-reperfusion injury) | 1-4, 6 |
| `hvm` | Ctrl1A2, Ctrl1A4 (mouse); HUK1_COR1, HUK1_MED1 (human, both cortex), on the shared 1:1 orthologs | 1, 3, 5 |

## Install

```bash
git clone https://github.com/edmundtsou/COAST_paper.git
cd COAST_paper
pip install -e .
```

Python ≥ 3.10. This installs COAST from GitHub and the small `coast_paper` package the scripts share. Figs. 1-3 also
call `vips` and `vipsheader` ([libvips](https://www.libvips.org/)) to crop the H&E. The Fig. 3e baselines need
scFates (`pip install -e ".[baselines]"`), plus Slingshot in R and GASTON in their own environments (see
`scripts/fig3_baselines.py`).

## Data

The data will be released with the paper and are not part of this repository. Every script reads `data/` and writes
`results/` (change them with `--data-root` and `--results-root`):

```
data/
  <section>/square_002um/      Space Ranger output of the Visium HD run at 2 um (binned_outputs/square_002um)
  <section>.geojson            segmentation of the section's H&E: one polygon per tubule cross-section, with its class
  <section>.tif                full-resolution H&E image (Figs. 1-3)
  orthologs.csv                HCOP human-mouse orthologs (columns human_symbol, mouse_symbol)
  pathway_gene_sets/           Enrichr libraries Reactome_2022, MSigDB_Hallmark_2020, KEGG_2019_Mouse (.json)
  cells/                       bin2cell cells (Fig. 4c): mouse/ and <slice>_bin2cell_cells_unfiltered.h5ad
  segmentation_reference/      manual outlines of the held-out Ctrl1A2 blocks (Fig. 2)
```

`inputs/` holds the small frozen gene lists the screens use: the transporter pairs whose handoffs are followed, and
the transport and injury programs of Fig. 6.

## Reproduce the paper

Run from the repository root, in this order (later steps read the outputs of earlier ones):

```bash
# the two COAST fits: bins -> units -> QC -> two passes -> curve (results/coast_runs/<fit>/)
python scripts/coast_fit.py --run aki
python scripts/coast_fit.py --run hvm
python scripts/gene_sets.py

# Fig. 3: robustness reruns, baselines, depth from the capsule, then the panels
python scripts/fig3_robustness.py --run aki && python scripts/fig3_robustness.py --run aki --score
python scripts/fig3_robustness.py --run hvm && python scripts/fig3_robustness.py --run hvm --score
python scripts/fig3_baselines.py --rscript <r-env>/bin/Rscript --gaston-python <gaston-env>/bin/python
python scripts/fig3_depth.py
python scripts/fig3_panels.py

# Fig. 4: continuous vs discrete along the PT, and COAST on single cells
python scripts/fig4_screen.py
python scripts/fig4_label_check.py
python scripts/fig4_linear_gain.py
python scripts/fig4_sc.py
python scripts/fig4_panels.py

# Fig. 5: mouse vs human along the PT
python scripts/fig5_screen.py
python scripts/shape_clusters.py --run hvm
python scripts/fig5_interpret.py
python scripts/fig5_panels.py
python scripts/fig5_figure.py

# Fig. 6: control vs AKI along the PT
python scripts/fig6_placement.py
python scripts/fig6_screen.py
python scripts/shape_clusters.py --run aki
python scripts/fig6_interpret.py
python scripts/fig6_panels.py
python scripts/fig6_figure.py

# Figs. 1 and 2, and the numbers quoted in the text
python scripts/fig1_panels.py
python scripts/fig2_gallery.py
python scripts/fig2_classes.py
python scripts/paper_numbers.py
```

The screens fit every gene and run for tens of minutes each; `--jobs` sets the number of parallel fits. Set
`OMP_NUM_THREADS=1` when running them with many jobs.

The two fits are sensitive to the BLAS thread count: PCA and Harmony sum in a different order with a different number
of threads, and Leiden can then split a few clusters differently. Run `coast_fit.py` with the default thread
settings (no `OMP_NUM_THREADS`), as the paper's fits were run; with 8 threads, for example, about 1% of the control /
AKI units change label.

## What each script does

| Script | What it does |
|---|---|
| `coast_fit.py` | The two fits with COAST: `io.read_visium_hd` and `io.read_segmentation`, `pp.bins_to_units` (hvm on the shared orthologs), QC (`pp.filter_units`, `pp.doublets`), two passes of `pp.integrate` + Leiden + `tl.label_clusters`, and `tl.pseudostructure`. Also provides `two_pass` for the reruns of Figs. 3d and 6. |
| `gene_sets.py` | Pathway gene sets of the set screens, mapped onto mouse symbols and the genes measured in both fits. |
| `fig1_panels.py` | Fig. 1: H&E and count maps of the six sections, segmentation and bin aggregation, Harmony, the curve, and example gradients. |
| `fig2_gallery.py`, `fig2_classes.py` | Fig. 2: segmentation tiles on sections the model never trained on, class maps of every section. |
| `fig3_robustness.py` | Fig. 3d: reruns with subsets of tubules, thinned reads, subsets and halves of the integration genes, scored against the reference coordinate. |
| `fig3_baselines.py`, `fig3_slingshot.R` | Fig. 3e: DPT, scFates, Slingshot and GASTON, scored like the pseudostructure coordinate. |
| `fig3_depth.py` | Fig. 3f: distance of every cross-section from the renal capsule on the H&E, against the coordinate. |
| `fig3_panels.py`, `fig3_common.py` | Fig. 3 panels; shared definitions (segment order, the per-section ρ). |
| `fig4_screen.py` | Fig. 4 screen: genes whose pattern along the PT the S1/S2/S3 means cannot express (`tl.test_genes` against the clusters, `tl.fit_curves`). |
| `fig4_label_check.py`, `fig4_linear_gain.py` | Fig. 4 checks: each call within a single label, and the deviance the curve explains beyond straight lines through the clusters. |
| `fig4_sc.py`, `fig4_sc_gpu.py` | Fig. 4c: COAST on bin2cell single cells of the same sections, exactly as on tubules (the GPU version uses rapids-singlecell). |
| `fig4_panels.py` | Fig. 4 panels. |
| `fig5_screen.py`, `fig6_screen.py` | Mouse vs human (Fig. 5) and control vs AKI (Fig. 6) along the PT: curves of every gene on COAST's coordinate, gradients, transporter handoffs, pathways. |
| `shape_clusters.py` | Figs. 5f / 6f: genes whose shape along the PT changes between the groups, against mixed-section splits, in Ward clusters; then pathways. |
| `fig5_interpret.py`, `fig6_interpret.py` | Follow-up checks of every call (admixture, cortical units, robustness of pathway calls and handoff shifts). |
| `fig6_placement.py` | Fig. 6 check: the IR sections placed on an axis built without the injury-responsive genes. |
| `fig5_panels.py`, `fig6_panels.py`, `fig5_figure.py`, `fig6_figure.py`, `fig56_examples.py` | Panels and the composed Figs. 5 and 6; example genes and pathways chosen by stated rules from the current screen. |
| `paper_numbers.py` | Every number quoted in the Fig. 5 and 6 Results, recomputed from the outputs. |

The shared package `coast_paper` holds the data layout (`layout.py`), the marker panels and labels of the mouse
kidney (`marker_panels.yaml`), the pathway set builder (`pathways.py`) and the handoff position (`handoffs.py`).

## Not yet here

- The segmentation model: training and inference code (placeholder in [`segmentation/`](segmentation/)).
- Two Extended Data panels of Fig. 5 (genes zonated by orthology class; human / mouse gradient attenuation against
  external atlases) read tables from analyses not yet in this repository; `fig5_panels.py` skips them when the tables
  are absent.
