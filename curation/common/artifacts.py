from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

STAGES = {
    "01-dataset-audit",
    "02-annotation-audit",
    "03-class-distribution",
    "04-duplicate-analysis",
    "05-image-quality",
    "06-active-label-cleaning",
    "07-curation-report",
}

def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()

def load_config(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    with (root / "curation" / "config.yaml").open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)

def stage_output_dir(
    stage: str,
    repo_root: str | Path,
    *,
    create: bool = True,
) -> Path:
    if stage not in STAGES:
        raise ValueError(f"Unknown curation stage: {stage}")
    root = Path(repo_root).resolve()
    output = root / "curation" / "outputs" / stage
    if create:
        output.mkdir(parents=True, exist_ok=True)
    return output

def load_manifest(stage: str, repo_root: str | Path) -> dict[str, Any]:
    path = stage_output_dir(stage, repo_root, create=False) / "manifest.yaml"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as stream:
        manifest = yaml.safe_load(stream) or {}
    if manifest.get("schema_version") != 1:
        raise ValueError(f"Unsupported manifest schema in {path}")
    return manifest


def ordered_rows_fingerprint(frame: Any, columns: Iterable[str]) -> str:
    """Hash selected rows in their current order using a stable JSON encoding."""
    selected = list(columns)
    digest = hashlib.sha256()
    for values in frame[selected].itertuples(index=False, name=None):
        line = json.dumps(
            [None if value is None else str(value) for value in values],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()

def stable_key(*parts: Any) -> str:
    text = "\x1f".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _repo_relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()

def write_manifest(
    stage: str,
    producer: str,
    *,
    repo_root: str | Path,
    inputs: Mapping[str, str | Path],
    parameters: Mapping[str, Any],
    artifacts: Iterable[str | Path],
    summary: Mapping[str, Any],
    compatibility: Mapping[str, Any] | None = None,
) -> Path:
    """Write a deterministic stage manifest; no clock-derived fields are used."""
    root = Path(repo_root).resolve()
    stage_dir = stage_output_dir(stage, root)
    config_path = root / "curation" / "config.yaml"

    input_entries = {}
    for name, value in sorted(inputs.items()):
        path = Path(value)
        input_entries[name] = {
            "path": _repo_relative(path, root),
            "sha256": sha256_file(path),
        }

    artifact_entries = []
    for value in sorted((Path(item) for item in artifacts), key=lambda p: p.as_posix()):
        if not value.is_file():
            raise FileNotFoundError(f"Manifest artifact does not exist: {value}")
        artifact_entries.append(
            value.resolve().relative_to(stage_dir.resolve()).as_posix()
        )

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "producer": producer,
        "configuration": {
            "path": _repo_relative(config_path, root),
            "sha256": sha256_file(config_path),
        },
        "inputs": input_entries,
        "parameters": dict(parameters),
        "artifacts": artifact_entries,
        "summary": dict(summary),
    }
    if compatibility:
        manifest["compatibility"] = dict(compatibility)

    manifest_path = stage_dir / "manifest.yaml"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as stream:
        yaml.safe_dump(
            manifest,
            stream,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
    return manifest_path