"""Manifest loading: relative paths resolve against the manifest file, not the cwd."""
from pathlib import Path

import pytest

from kidney_panoptic.data.manifest import load_manifest

HEADER = "slide_id,image_path,geojson_path,split\n"


def _layout(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    (data / "slides").mkdir(parents=True)
    (data / "annotations").mkdir()
    (data / "slides" / "S1.tif").write_bytes(b"")
    (data / "annotations" / "S1.geojson").write_text("{}")
    m = data / "manifest.csv"
    m.write_text(HEADER + "S1,slides/S1.tif,annotations/S1.geojson,train\n")
    return m


def test_relative_paths_resolve_against_manifest_dir(tmp_path, monkeypatch):
    m = _layout(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    (row,) = load_manifest(m)
    assert Path(row["image_path"]) == (tmp_path / "data" / "slides" / "S1.tif").resolve()
    assert Path(row["geojson_path"]).exists()


def test_absolute_paths_are_kept(tmp_path):
    m = _layout(tmp_path)
    slide = (tmp_path / "data" / "slides" / "S1.tif").resolve()
    geo = (tmp_path / "data" / "annotations" / "S1.geojson").resolve()
    m.write_text(HEADER + f"S1,{slide},{geo},val\n")
    (row,) = load_manifest(m)
    assert row["image_path"] == str(slide)


def test_missing_slide_fails_at_load(tmp_path):
    m = _layout(tmp_path)
    (tmp_path / "data" / "slides" / "S1.tif").unlink()
    with pytest.raises(FileNotFoundError, match="image_path"):
        load_manifest(m)
    assert load_manifest(m, check_paths=False)[0]["slide_id"] == "S1"
