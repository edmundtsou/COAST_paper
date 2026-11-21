#!/usr/bin/env python
"""Download the released model weights and whole-slide images from Zenodo.

    python scripts/download_data.py                 # weights only (~60 MB)
    python scripts/download_data.py --slides test   # + the 3 test-set slides (~5 GB)
    python scripts/download_data.py --slides all    # + every slide (~9 GB)
    python scripts/download_data.py --slides Ctrl_1A2 IR_2A2

Weights go to ``weights/``, slides to ``data/slides/``, which is where the configs,
manifests and ``scripts/reproduce_benchmarks.sh`` expect them. Every file is checked against
the MD5 that Zenodo publishes for it, and the two weight files are also checked against the
SHA-256 values below. Files already present with the right checksum are skipped, so the
command can be re-run after an interruption.

Annotations are NOT downloaded: they are small and live in ``data/annotations/`` in this
repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# TODO(release): set to the Zenodo record id once the deposit is published, e.g. "1234567".
ZENODO_RECORD = None
ZENODO_API = "https://zenodo.org/api/records/{record}"

WEIGHTS = {
    "mouse_weights.pt": "f913452838ed963fd8d75ad82cdd9459afa3694fbafe988d0ae3a974c515c08d",
    "human_weights.pt": "9de7df6f4aa7ddd8937b99b5d7d26cb8a33d97abbefd12a18633d43f4cde981a",
}

SLIDE_SETS = {
    "train": ["Nx_24h_1.ndpi", "Nx_24h_50.ndpi", "Nx_24h_100.ndpi",
              "Nx_4wk_001.ndpi", "Nx_4wk_100.ndpi", "Ctrl_1A2.tif", "HUK1_COR_1.tif"],
    "val": ["Nx_4wk_050.ndpi", "Ctrl_1A2.tif", "HUK1_COR_1.tif"],
    "test": ["Ctrl_1A2.tif", "IR_2A2.tif", "HUK1_MED_1.tif"],
}
SLIDE_SETS["all"] = sorted({f for v in SLIDE_SETS.values() for f in v})


def file_hash(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_listing(record: str) -> dict[str, dict]:
    with urllib.request.urlopen(ZENODO_API.format(record=record), timeout=60) as r:
        meta = json.load(r)
    out = {}
    for f in meta.get("files", []):
        key = f.get("key") or f.get("filename")
        algo, _, digest = str(f.get("checksum", "")).partition(":")
        out[key] = {"url": f["links"]["self"], "size": int(f.get("size", 0)),
                    "md5": digest if algo == "md5" else None}
    return out


def download(url: str, dest: Path, size: int):
    tmp = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    done = 0
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 22):
            f.write(chunk)
            done += len(chunk)
            if size:
                print(f"\r  {dest.name}: {done / 1e6:8.1f} / {size / 1e6:.1f} MB", end="", flush=True)
    print()
    tmp.replace(dest)


def resolve_slides(requested: list[str]) -> list[str]:
    names: list[str] = []
    for item in requested:
        if item in SLIDE_SETS:
            names += SLIDE_SETS[item]
            continue
        matches = [f for f in SLIDE_SETS["all"] if Path(f).stem == item or f == item]
        if not matches:
            raise SystemExit(f"Unknown slide or set '{item}'. Sets: {sorted(SLIDE_SETS)}; "
                             f"slides: {[Path(f).stem for f in SLIDE_SETS['all']]}")
        names += matches
    return list(dict.fromkeys(names))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--slides", nargs="*", default=[],
                   help="slide set (train | val | test | all) or slide names")
    p.add_argument("--no-weights", action="store_true", help="skip the model weights")
    p.add_argument("--record", default=ZENODO_RECORD, help="Zenodo record id override")
    args = p.parse_args(argv)

    if not args.record:
        raise SystemExit(
            "The Zenodo record id is not set yet. Edit ZENODO_RECORD in "
            "scripts/download_data.py or pass --record <id>.")

    wanted: list[tuple[str, Path]] = []
    if not args.no_weights:
        wanted += [(n, REPO / "weights" / n) for n in WEIGHTS]
    wanted += [(n, REPO / "data" / "slides" / n) for n in resolve_slides(args.slides)]
    if not wanted:
        raise SystemExit("Nothing to download.")

    listing = fetch_listing(str(args.record))
    failed = []
    for name, dest in wanted:
        entry = listing.get(name)
        if entry is None:
            print(f"MISSING  {name} is not in Zenodo record {args.record}")
            failed.append(name)
            continue
        if dest.is_symlink() or (dest.exists() and entry["md5"]
                                 and file_hash(dest, "md5") == entry["md5"]):
            print(f"ok       {dest.relative_to(REPO)} (already present)")
            continue
        download(entry["url"], dest, entry["size"])
        if entry["md5"] and file_hash(dest, "md5") != entry["md5"]:
            print(f"BAD MD5  {name}")
            failed.append(name)
            continue
        if name in WEIGHTS and file_hash(dest, "sha256") != WEIGHTS[name]:
            print(f"BAD SHA  {name}: does not match the released weights")
            failed.append(name)
            continue
        print(f"ok       {dest.relative_to(REPO)}")

    if failed:
        raise SystemExit(f"{len(failed)} file(s) failed: {failed}")


if __name__ == "__main__":
    sys.exit(main())
