#!/usr/bin/env bash
# Whole-slide inference over every slide in a folder, then one summary CSV.
#
#   bash scripts/batch_infer.sh <weights.pt> <slide-dir> <out-dir> [gpu] [extra wsi_infer args...]
#
# Examples:
#   bash scripts/batch_infer.sh weights/mouse_weights.pt /data/my_slides results/my_batch 0
#   # flat TIFF exports without a usable resolution tag: pin the level and mpp
#   bash scripts/batch_infer.sh weights/mouse_weights.pt /data/tifs results/tifs 0 \
#       --set wsi.level=0 wsi.manual_mpp=0.44068
#
# Each slide gets <out-dir>/<slide-stem>/ (instances.geojson, instance_map.npz,
# summary.json, overlay.png). Slides whose summary.json already exists are skipped, so the
# batch can be stopped and restarted. Slide extensions: .ndpi .svs .tif .tiff .mrxs .scn
# .vms .bif. Check a new scanner's resolution first with wsi_infer.py --dry-run.
set -uo pipefail
cd "$(dirname "$0")/.."

WEIGHTS="${1:?usage: batch_infer.sh <weights.pt> <slide-dir> <out-dir> [gpu] [extra args]}"
SLIDES="${2:?slide-dir}"
OUT="${3:?out-dir}"
GPU="${4:-0}"
shift $(( $# < 4 ? $# : 4 ))

mkdir -p "$OUT"
shopt -s nullglob nocaseglob
n_ok=0; n_skip=0; n_fail=0
for slide in "$SLIDES"/*.{ndpi,svs,tif,tiff,mrxs,scn,vms,bif}; do
  stem="$(basename "${slide%.*}")"
  dest="$OUT/$stem"
  if [[ -f "$dest/summary.json" ]]; then
    echo "skip  $stem (done)"; n_skip=$((n_skip + 1)); continue
  fi
  echo "=== $stem  $(date -Is)"
  if python -u scripts/wsi_infer.py --checkpoint "$WEIGHTS" --slide "$slide" \
       --out-dir "$dest" --save-viz --gpu "$GPU" "$@"; then
    n_ok=$((n_ok + 1))
  else
    echo "FAIL  $stem"; n_fail=$((n_fail + 1))
  fi
done
echo "done: $n_ok run, $n_skip skipped, $n_fail failed"
python scripts/collect_summaries.py "$OUT"
[[ $n_fail -eq 0 ]]
