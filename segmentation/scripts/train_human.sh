#!/usr/bin/env bash
# Retrain the human model (released as weights/human_weights.pt) from scratch.
#
#   python scripts/download_data.py --no-weights --slides HUK1_COR_1
#   bash scripts/train_human.sh [gpu]
#
# Same steps as scripts/train_mouse.sh with configs/human.yaml: 640 px patches into
# data/patches_human/, the overfit gate, then 60 epochs into runs/human/.
#
# Use runs/human/best_pq.pt, not last.pt. With a held-out split the overfit is sharp:
# held-out PQ peaked at epoch 25 (the released weights) and fell afterwards while the
# training loss kept falling.
set -euo pipefail
cd "$(dirname "$0")/.."
GPU="${1:-0}"

if [[ -z "$(ls -A data/patches_human 2>/dev/null)" ]]; then
  python -u scripts/extract_patches.py --config configs/human.yaml
fi
python -u scripts/overfit.py --config configs/human.yaml --steps 250 --gpu "$GPU" \
  --out results/overfit_human
python -u scripts/train.py --config configs/human.yaml --out runs/human \
  --gpu "$GPU" --max-val-patches 200
