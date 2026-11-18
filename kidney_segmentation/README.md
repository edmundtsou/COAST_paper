# kidney_panoptic: tubule and glomerulus segmentation

This is the segmentation component of the COAST paper (citation below). It outlines every
tubule and glomerulus on an H&E-stained kidney whole-slide image as a separate,
individually labelled object. Output is QuPath-loadable GeoJSON, a slide-wide instance map,
and per-slide counts, areas and densities.

There are two models, trained separately and never mixed:

| model | species / tissue | classes | resolution | weights |
|---|---|---|---|---|
| mouse | mouse kidney | proximal tubule, distal tubule, collecting duct, glomerulus | 0.44 µm/px (20×) | `weights/mouse_weights.pt` |
| human | human kidney cortex | tubule, glomerulus | 0.50 µm/px | `weights/human_weights.pt` |

Vessels, nerves and blood cells are not segmented.

## Results

Each benchmark below was scored by `scripts/benchmark_segmentation.py` on annotations the
model did not train on. The values are pooled over all objects. Brackets give 95%
cluster-bootstrap intervals over 1024 px tiles.

| set | sections | objects | PQ | Dice per object | recall | precision |
|---|---|---|---|---|---|---|
| Mouse test, pooled | 2 | 355 | 0.804 [0.776, 0.831] | 0.823 | 0.887 | 0.963 |
| Human test | 1 | 138 | 0.882 [0.849, 0.899] | 0.918 | 0.971 | 0.993 |
| Mouse validation | 2 | 511 | 0.800 [0.763, 0.834] | 0.828 | 0.886 | 0.928 |
| Human validation | 1 | 317 | 0.887 [0.851, 0.914] | 0.920 | 0.965 | 0.975 |

The test sets were annotated after the models and every decode setting were fixed. The mouse
test pools a control section (150 objects) and an ischemia-reperfusion section (205 objects,
including 54 tubules with intraluminal casts). The full tables are in `results/benchmark_*/`:
`benchmark.json` (all metrics with intervals), `objects.csv` (one row per object),
`tiles.csv`, `slides.csv` and `failure_report.md`.

The intervals resample tiles within the scored sections only. With one or two sections per
set, they say nothing about variation between slides, scanners or labs.

## Installation

Linux and an NVIDIA GPU are required. The results were produced with Python 3.10, PyTorch
2.6 and CUDA 12.4 on an RTX 6000 Ada (48 GB).

```bash
git clone https://github.com/edmundtsou/COAST_paper
cd COAST_paper/kidney_segmentation
conda env create -f environment.yml
conda activate kidney_panoptic
pytest tests/          # CPU only, a few seconds
```

If you do not use conda, install PyTorch for your CUDA version from
[pytorch.org](https://pytorch.org), then run `pip install -r requirements.txt`.

**Encoder access.** The model's frozen encoder is
[OpenMidnight](https://huggingface.co/SophontAI/OpenMidnight) (Apache-2.0). It downloads
from the Hugging Face Hub on first use, about 4.5 GB, and is cached under `HF_HOME`. The
repository is gated. Accept its terms on the model page once, then log in:

```bash
hf auth login
```

The encoder's model code is fetched once through `torch.hub` from the
[facebookresearch/dinov2](https://github.com/facebookresearch/dinov2) GitHub repository
and is cached under `~/.cache/torch/hub`. The first run therefore needs internet access.

## Download the weights and data

The weights and the whole-slide images are on Zenodo: **[TODO: Zenodo DOI]**. The
annotations are in this repository, in `data/annotations/`.

```bash
python scripts/download_data.py                  # weights only, about 60 MB
python scripts/download_data.py --slides test    # + the 3 test slides
python scripts/download_data.py --slides all     # + all 10 slides, about 9 GB
```

Weights go to `weights/` and slides go to `data/slides/`. Each file is checked against its
published checksum.

| slide | species | used for |
|---|---|---|
| `Nx_24h_1`, `Nx_24h_50`, `Nx_24h_100`, `Nx_4wk_001`, `Nx_4wk_100` (.ndpi) | mouse | training |
| `Nx_4wk_050` (.ndpi) | mouse | validation |
| `Ctrl_1A2` (.tif) | mouse | training and validation (alternating 2048 px blocks), and test (a separately annotated region at least 158 µm from every training patch) |
| `IR_2A2` (.tif) | mouse | test |
| `HUK1_COR_1` (.tif) | human | training and validation (interleaved 4096 px blocks) |
| `HUK1_MED_1` (.tif) | human | test |

The manifests in `data/` (`manifest_mouse.csv`, `manifest_human.csv`, `manifest_test.csv`)
define every split. Their paths are relative to `data/`.

## Run on your own slides

```bash
python scripts/wsi_infer.py --checkpoint weights/mouse_weights.pt \
  --slide /path/to/slide.ndpi --out-dir results/my_slide --save-viz --gpu 0
```

Use `weights/human_weights.pt` for human tissue. The released weights already contain the decode
settings used in the paper, including 8× test-time augmentation, so you do not need extra
flags. Expect roughly 40–60 minutes for a whole mouse section on one RTX 6000 Ada. To trade
accuracy for about 8× speed, add `--tta none`.

**Check the resolution first.** The model reads one native pyramid level and never
resamples it. It picks the level closest to 0.44 µm/px (mouse) or 0.50 µm/px (human) from
the slide's metadata, and warns if no level is within 10%. A dry run prints the choice
without loading the model:

```bash
python scripts/wsi_infer.py --checkpoint weights/mouse_weights.pt \
  --slide /path/to/slide.ndpi --out-dir /tmp/check --dry-run
```

Some slides have no usable resolution tag. Single-level TIFF exports often carry only a
print DPI, and the reader refuses those on purpose. For such a slide, give the level and
µm/px yourself:

```bash
  --set wsi.level=0 wsi.manual_mpp=0.44
```

Results at a resolution other than 0.44 / 0.50 µm/px, or from other stains, scanners or
organs, have not been validated.

**Outputs** in `--out-dir`:

| file | content |
|---|---|
| `instances.geojson` | one polygon per object with its class and score, in level-0 coordinates. To load it in QuPath, drag it onto the open slide. |
| `instance_map.npz` | int32 instance id per pixel at the working resolution (`--no-save-map` skips it) |
| `summary.json` | counts, areas (px² and mm²), density per mm² of tissue for each class, tissue area, glass rate, and the full config used |
| `overlay.png`, `tissue_mask.png` | downsampled visual check (`--save-viz`) |

**Many slides:**

```bash
bash scripts/batch_infer.sh weights/mouse_weights.pt /path/to/slides results/my_batch 0
```

This command runs every slide in the folder, skips slides that are already done, and
writes `results/my_batch/summary.csv` with one row per slide.

Any config value can be overridden with `--set a.b=value`. `configs/default.yaml` documents
every option and the measurement each default came from.

## Reproduce the paper's benchmarks

```bash
python scripts/download_data.py --slides val test
bash scripts/reproduce_benchmarks.sh 0          # GPU 0; about 4 h
```

This runs whole-slide inference on the five scored slides and then scores them. Output goes
to `results/reproduced/`. The script ends with `scripts/compare_benchmarks.py`, which prints
every headline metric next to the shipped value in `results/`.

## Retrain

```bash
python scripts/download_data.py --no-weights --slides train val
bash scripts/train_mouse.sh 0     # patches -> overfit sanity gate -> 60 epochs, about 3.5 h
bash scripts/train_human.sh 0
```

Training writes `runs/<model>/best_pq.pt`, selected by validation panoptic quality, not by
validation loss (see [ADR 0004](docs/adr/0004-checkpoint-selection-by-pq.md)). The
per-epoch losses of the released runs are in `runs/*/history.json`. GPU training is not
bit-for-bit deterministic, so a retrained model will differ slightly from the released one.
`scripts/make_release_checkpoint.py` shows how the released files were made from the
training checkpoints. The model weights are unchanged. Only the stored decode and inference
settings are edited.

## How it works

- **Encoder:** frozen OpenMidnight, a pathology DINOv2 ViT-g/14 with registers (1.1 B
  parameters). Features come from blocks 9, 19, 29 and 39.
- **Stem and decoder:** a trainable convolutional stem works on native pixels at strides
  1–16. A fusion decoder with 7.3 M trainable parameters combines it with the encoder
  features, so object boundaries are placed to the pixel
  ([ADR 0002](docs/adr/0002-full-res-stem-skips.md)).
- **Three heads:** a semantic class map; a boundary map (background, interior, boundary
  against background, boundary against a touching object); and a centre heatmap for
  glomeruli.
- **Decode:** marker-controlled watershed. Seeds are connected regions of high interior
  probability, and the boundary probability is the elevation. Each instance's class is the
  majority vote of its core pixels. Two guards stop an instance from annexing its
  neighbour's wall or the interstitium: a cap on flood distance from the seed, and a veto
  that carves touching-object walls out of the seeds.
- **No centroid-vector field.** Every predicted map is local, so tiled inference is
  seam-free by construction and test-time augmentation can average all 8 rotations and
  flips ([ADR 0001](docs/adr/0001-boundary-vs-centroid-hv.md)).
- **Partial labels:** annotated objects are trusted foreground. Glass, drawn background and
  a thin ring around each object are trusted background. All other unannotated tissue is
  ignored in the loss ([ADR 0003](docs/adr/0003-three-way-ignore-and-tissue-gate.md)).

Whole slides are predicted in 512 px tiles (640 px for human) under a Gaussian blend. The
decode runs in 2048 px windows with a one-tile halo, and objects that cross a window border
are stitched together.

## Known limitations

- **Merging is the main error.** Two touching tubules of the same type are sometimes
  returned as one object: 11.8% of objects in the pooled mouse test set, 1.4% in the human
  test set.
- **The human labels are partly model-derived.** Of the 1,547 human training and
  validation objects, 220 were drawn by hand. The rest are predictions of a preliminary
  model that a person reviewed and kept without editing, so that model's boundary bias is
  part of the labels. The human test set (138 objects) is fully hand-drawn.
- **Narrow data.** Ten sections in total, one scanner and one stain protocol per species.
  Nothing has been validated across scanners, stains or labs.
- **Fixed resolution.** The models see 0.44 / 0.50 µm/px only. See *Run on your own
  slides*.

## Repository layout

```
configs/        default.yaml (every option, with its reasoning), mouse.yaml, human.yaml
data/           manifests; annotations/ (GeoJSON); slides/ (downloaded)
docs/adr/       the design decisions behind the model
results/        the paper's benchmark tables
runs/           per-epoch training history of the released models
scripts/        wsi_infer, batch_infer, benchmark_segmentation, reproduce_benchmarks,
                train / train_*.sh, extract_patches, overfit, eval_regions, download_data, ...
src/kidney_panoptic/   data, models, losses, infer, postprocess, eval
tests/          CPU unit tests
```

## Citation

If you use this code, the weights or the annotations, please cite:

> TODO: COAST paper citation and DOI.

## License

The code is released under the MIT license (see `LICENSE`). The encoder weights
(OpenMidnight) are distributed by their authors under Apache-2.0 and are downloaded from
their repository, not redistributed here.
