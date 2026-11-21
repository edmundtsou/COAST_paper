#!/usr/bin/env bash
# Reproduce every segmentation benchmark reported in the paper, from the released weights.
#
#   python scripts/download_data.py --slides val test     # weights + 6 slides
#   bash scripts/reproduce_benchmarks.sh [gpu] [out-root]
#
# Step 1 runs whole-slide inference on the five slides the benchmarks score (about 4 h on one
# RTX 6000 Ada with 8x TTA; a slide already done is skipped). Step 2 scores those
# predictions against the annotations in data/annotations/ with
# scripts/benchmark_segmentation.py (about 20 s per benchmark, plus a few minutes for the
# stain-drift probe on the two validation runs).
#
# Output goes to <out-root> (default results/reproduced/) so it can be compared with the
# shipped results/benchmark_*/benchmark.json, which are what the paper reports.
#
# Resolution: Ctrl_1A2, IR_2A2 and the HUK1 slides are flat single-level TIFF exports whose
# resolution tag is not a scan resolution, so their level and mpp are pinned on the command
# line exactly as in the original runs. The Nx .ndpi slides carry their own pyramid metadata
# and the level is picked from it.
set -euo pipefail
cd "$(dirname "$0")/.."

GPU="${1:-0}"
OUT="${2:-results/reproduced}"
S=data/slides
mkdir -p "$OUT"

infer() {  # infer <weights> <slide> <out-dir> [--set ...]
  local w="$1" slide="$2" dest="$3"; shift 3
  if [[ -f "$dest/summary.json" ]]; then echo "skip  $dest (done)"; return; fi
  echo "=== inference: $slide -> $dest  $(date -Is)"
  python -u scripts/wsi_infer.py --checkpoint "$w" --slide "$slide" --out-dir "$dest" \
    --gpu "$GPU" "$@"
}

# ---- 1. whole-slide predictions -------------------------------------------------------
MOUSE_FLAT=(--set wsi.level=0 wsi.manual_mpp=0.44068)
HUMAN_FLAT=(--set wsi.level=0 wsi.manual_mpp=0.5)
infer weights/mouse_weights.pt $S/Ctrl_1A2.tif   "$OUT/mouse_Ctrl_1A2"     "${MOUSE_FLAT[@]}"
infer weights/mouse_weights.pt $S/IR_2A2.tif     "$OUT/mouse_IR_2A2"       "${MOUSE_FLAT[@]}"
infer weights/mouse_weights.pt $S/Nx_4wk_050.ndpi "$OUT/mouse_Nx_4wk_050"
infer weights/human_weights.pt $S/HUK1_COR_1.tif "$OUT/human_HUK1_COR_1" "${HUMAN_FLAT[@]}"
infer weights/human_weights.pt $S/HUK1_MED_1.tif "$OUT/human_HUK1_MED_1" "${HUMAN_FLAT[@]}"

# ---- 2. benchmarks --------------------------------------------------------------------
bench() { echo "=== benchmark: $1"; python -u scripts/benchmark_segmentation.py --out-dir "$OUT/$1" "${@:2}"; }

# Validation (held-out blocks / held-out slide). --stain-drift re-runs the model on crops.
bench benchmark_mouse_val --manifest data/manifest_mouse.csv --split val \
  --pred Ctrl_1A2_val="$OUT/mouse_Ctrl_1A2" --pred Nx_4wk_050="$OUT/mouse_Nx_4wk_050" \
  --stain-drift --checkpoint weights/mouse_weights.pt --gpu "$GPU"
bench benchmark_human_val --manifest data/manifest_human.csv --split val \
  --pred HUK1_COR_1_human_val="$OUT/human_HUK1_COR_1" \
  --stain-drift --checkpoint weights/human_weights.pt --gpu "$GPU"

# Independent test sets, annotated after the models and decode settings were fixed.
bench benchmark_mouse_test_ctrl1a2 --manifest data/manifest_test.csv --split test \
  --pred Ctrl_1A2_test="$OUT/mouse_Ctrl_1A2"
bench benchmark_mouse_test_ir2a2 --manifest data/manifest_test.csv --split test \
  --pred IR_2A2_test_casts="$OUT/mouse_IR_2A2"
bench benchmark_mouse_test_pooled --manifest data/manifest_test.csv --split test \
  --pred Ctrl_1A2_test="$OUT/mouse_Ctrl_1A2" --pred IR_2A2_test_casts="$OUT/mouse_IR_2A2"
bench benchmark_mouse_test_pooled_nocasts --manifest data/manifest_test.csv --split test \
  --pred Ctrl_1A2_test="$OUT/mouse_Ctrl_1A2" --pred IR_2A2_test="$OUT/mouse_IR_2A2"
bench benchmark_human_test --manifest data/manifest_test.csv --split test \
  --pred HUK1_MED_1_test="$OUT/human_HUK1_MED_1"

python scripts/compare_benchmarks.py results "$OUT"
