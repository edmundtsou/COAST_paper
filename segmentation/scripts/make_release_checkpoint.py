#!/usr/bin/env python
"""Turn a training checkpoint into the released inference checkpoint.

    python scripts/make_release_checkpoint.py --model mouse \
        --src runs/mouse/best_pq.pt --out weights/mouse_weights.pt
    python scripts/make_release_checkpoint.py --model human \
        --src runs/human/best_pq.pt --out weights/human_weights.pt

This is how ``weights/*.pt`` were produced; it is kept so the released files can be traced
back to their training checkpoints. The model weights are copied unchanged. Only the stored
config, which ``wsi_infer.py`` uses as its configuration, is edited:

* the optimizer state is dropped (inference does not need it; 88 MB -> 29 MB);
* the decode settings used for every result in the paper are written in, so a plain
  ``wsi_infer.py`` call reproduces them without extra ``--set`` flags. These are the two
  interstitium-annexation guards (see ``configs/mouse.yaml`` / ``configs/human.yaml``) and
  8x D4 test-time augmentation. Both checkpoints were trained before those settings existed
  in the config, so they are not in the stored config otherwise;
* resolution handling is made slide-agnostic: ``wsi.level`` is unset so the pyramid level
  is picked by ``wsi.target_mpp``, and ``wsi.manual_mpp`` is unset so the slide's own
  metadata is used. Slides without usable metadata need ``--set wsi.level=0
  wsi.manual_mpp=<um/px>``, as in ``scripts/reproduce_benchmarks.sh``;
* machine-specific entries (training device, absolute config directory, data paths) are
  reset to repository-relative values.

A ``release`` block records the source checkpoint's SHA-256 and the new value of every
setting that was edited. The previous values are printed when the script runs but not
stored, because they hold development-machine paths that mean nothing outside it.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
import torch

from kidney_panoptic.utils.checkpoint import load_checkpoint

# Per-model edits to the stored config, as (dotted key, value).
RELEASE_SETTINGS = {
    "mouse": {
        "decode.max_flood_distance_px": 8,
        "decode.touching_seed_veto": 0.05,
        "infer.tta": "d4",
        "wsi.level": None,
        "wsi.manual_mpp": None,
        "device": "cuda:0",
        "manifest": "../data/manifest_mouse.csv",
        "paths.patches_dir": "../data/patches_mouse",
    },
    "human": {
        "decode.max_flood_distance_px": 10,
        "decode.touching_seed_veto": 0.05,
        "infer.tta": "d4",
        "wsi.level": None,
        "wsi.manual_mpp": None,
        "device": "cuda:0",
        "manifest": "../data/manifest_human.csv",
        "paths.patches_dir": "../data/patches_human",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def set_dotted(cfg: dict, key: str, value):
    *parents, leaf = key.split(".")
    node = cfg
    for p in parents:
        node = node.setdefault(p, {})
    old = node.get(leaf, "<unset>")
    node[leaf] = value
    return old


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True, choices=sorted(RELEASE_SETTINGS))
    p.add_argument("--src", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)

    ckpt = load_checkpoint(args.src)
    cfg = copy.deepcopy(ckpt["config"])
    cfg.pop("_config_dir", None)

    changes, previous = {}, {}
    for key, value in RELEASE_SETTINGS[args.model].items():
        old = set_dotted(cfg, key, value)
        if old != value:
            changes[key] = value
            previous[key] = old

    out = {k: v for k, v in ckpt.items() if k != "optimizer_state"}
    out["config"] = cfg
    out["release"] = {
        "name": args.model,
        "source_checkpoint": args.src.name,
        "source_sha256": sha256(args.src),
        "source_epoch": int(ckpt.get("epoch", -1)),
        "config_set": changes,
        "dropped": ["optimizer_state"] if "optimizer_state" in ckpt else [],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(out, args.out)

    print(f"{args.model}: {args.src} (epoch {out['release']['source_epoch']}) -> {args.out}")
    for k, v in changes.items():
        print(f"  {k}: {previous[k]!r} -> {v!r}")
    print(f"  size   {args.out.stat().st_size / 1e6:.1f} MB")
    print(f"  sha256 {sha256(args.out)}")


if __name__ == "__main__":
    sys.exit(main())
