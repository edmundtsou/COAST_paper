#!/usr/bin/env bash
# Retrain the mouse model (released as weights/mouse_weights.pt) from scratch.
#
#   python scripts/download_data.py --no-weights --slides Nx_24h_1 Nx_24h_50 Nx_24h_100 \
#       Nx_4wk_001 Nx_4wk_050 Nx_4wk_100 Ctrl_1A2
#   bash scripts/train_mouse.sh [gpu]
#
# 1. extracts 512 px training patches into data/patches_mouse/ (skipped if it has files),
# 2. runs the overfit sanity gate (a few minutes; must print PASS),
# 3. trains for 60 epochs into runs/mouse/ (~3.5 h on one RTX 6000 Ada).
#
# Use runs/mouse/best_pq.pt, selected by validation panoptic quality (docs/adr/0004),
# not last.pt. The released weights are epoch 35 of the original run. GPU training is not
# bit-for-bit deterministic, so a retrained model will differ slightly from the release.
# For whole-slide inference with a retrained checkpoint pass --tta d4 to wsi_infer.py, or
# convert it with scripts/make_release_checkpoint.py.
set -euo pipefail
cd "$(dirname "$0")/.."
GPU="${1:-0}"

if [[ -z "$(ls -A data/patches_mouse 2>/dev/null)" ]]; then
  python -u scripts/extract_patches.py --config configs/mouse.yaml
fi
python -u scripts/overfit.py --config configs/mouse.yaml --steps 250 --gpu "$GPU" \
  --out results/overfit_mouse
python -u scripts/train.py --config configs/mouse.yaml --out runs/mouse \
  --gpu "$GPU" --max-val-patches 160
