from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from .artifacts import load_config, sha256_file

def _safe_extract(archive: Path, target: Path) -> None:
    target_root = target.resolve()
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            destination = (target / member.filename).resolve()
            if destination != target_root and target_root not in destination.parents:
                raise ValueError(f"Unsafe path in {archive.name}: {member.filename}")
        source.extractall(target)

def _ensure_extracted(archive: Path, target: Path) -> str:
    digest = sha256_file(archive)
    marker = target / ".source_sha256"
    if target.is_dir() and marker.is_file():
        if marker.read_text(encoding="utf-8").strip() == digest:
            return digest

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{target.name}-", dir=target.parent) as temp:
        staged = Path(temp) / target.name
        staged.mkdir()
        _safe_extract(archive, staged)
        (staged / ".source_sha256").write_text(digest, encoding="utf-8")

        if target.exists():
            shutil.rmtree(target)
        staged.replace(target)
    return digest

def prepare_dataset(repo_root: str | Path) -> dict[str, Path | str]:
    """Idempotently prepare the configured image and LabelMe archives."""
    root = Path(repo_root).resolve()
    config = load_config(root)
    dataset_config = config["dataset"]
    datasets_dir = root / "datasets"

    image_archive = datasets_dir / dataset_config["image_archive"]
    annotation_archive = datasets_dir / dataset_config["annotation_archive"]
    missing = [path for path in (image_archive, annotation_archive) if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Required dataset archive(s) missing:\n- " + "\n- ".join(map(str, missing))
        )

    images_dir = datasets_dir / dataset_config["image_directory"]
    annotations_dir = datasets_dir / dataset_config["annotation_directory"]
    image_hash = _ensure_extracted(image_archive, images_dir)
    annotation_hash = _ensure_extracted(annotation_archive, annotations_dir)

    return {
        "repo_root": root,
        "datasets_dir": datasets_dir,
        "image_archive": image_archive,
        "annotation_archive": annotation_archive,
        "images_dir": images_dir,
        "annotations_dir": annotations_dir,
        "image_archive_sha256": image_hash,
        "annotation_archive_sha256": annotation_hash,
    }