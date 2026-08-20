#!/usr/bin/env python3
"""Validate or normalize result JSONL files against the 2026-08-19 release IDs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANNOTATION = REPO_ROOT / "dataset" / "annotation.jsonl"
DEFAULT_RESULTS = REPO_ROOT / "results"
DEFAULT_RESULTS_MANIFEST = DEFAULT_RESULTS / "manifest.json"
DATASET_RELEASE_ID = "2026-08-19"
EXPECTED_SAMPLE_COUNT = 5024
EXPECTED_SORTED_IDS_SHA256 = (
    "1460946d9a7c94e9baab953b180f6a88d15af22e0deacfc4db8a091a88921b06"
)


def read_ground_truth(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: record is not an object")
            record_id = record.get("id")
            if not isinstance(record_id, str) or not record_id:
                raise ValueError(
                    f"{path}:{line_number}: missing non-empty string id"
                )
            if record_id in seen_ids:
                raise ValueError(f"{path}:{line_number}: duplicate id {record_id!r}")
            seen_ids.add(record_id)
            records.append(record)

    if len(records) != EXPECTED_SAMPLE_COUNT:
        raise ValueError(
            f"expected {EXPECTED_SAMPLE_COUNT} GT records, found {len(records)}"
        )
    ids_digest = hashlib.sha256(
        ("\n".join(sorted(seen_ids)) + "\n").encode("utf-8")
    ).hexdigest()
    if ids_digest != EXPECTED_SORTED_IDS_SHA256:
        raise ValueError(
            f"GT ID fingerprint mismatch: expected {EXPECTED_SORTED_IDS_SHA256}, "
            f"found {ids_digest}"
        )
    return records


def read_result_file(
    path: Path,
) -> tuple[list[tuple[str, dict[str, Any]]], list[str]]:
    records: list[tuple[str, dict[str, Any]]] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: invalid JSON ({exc})")
                continue
            if not isinstance(record, dict):
                errors.append(f"line {line_number}: record is not an object")
                continue
            record_id = record.get("id")
            if not isinstance(record_id, str) or not record_id:
                errors.append(f"line {line_number}: missing non-empty string id")
            elif record_id in seen_ids:
                errors.append(f"line {line_number}: duplicate id {record_id!r}")
            else:
                seen_ids.add(record_id)
            records.append((raw_line, record))
    return records, errors


def atomic_write_lines(path: Path, lines: list[str]) -> None:
    original_mode = stat.S_IMODE(path.stat().st_mode)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            os.fchmod(temp_file.fileno(), original_mode)
            temp_file.writelines(lines)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_path(path: Path) -> str:
    """Return a repository-relative path when possible, otherwise an absolute path."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotation", type=Path, default=DEFAULT_ANNOTATION)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Remove records outside the authoritative GT ID set.",
    )
    parser.add_argument(
        "--write-manifest",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write hashes for all validated result files.",
    )
    parser.add_argument(
        "--results-manifest",
        type=Path,
        default=DEFAULT_RESULTS_MANIFEST,
        help="Manifest whose result-file hashes must match.",
    )
    args = parser.parse_args()
    args.annotation = args.annotation.expanduser().resolve()
    args.results = args.results.expanduser().resolve()
    args.results_manifest = args.results_manifest.expanduser().resolve()
    if args.write_manifest is not None:
        args.write_manifest = args.write_manifest.expanduser().resolve()

    try:
        ground_truth = read_ground_truth(args.annotation)
    except (OSError, ValueError) as exc:
        print(f"ERROR: dataset: {exc}")
        return 1

    ground_truth_ids = {record["id"] for record in ground_truth}
    result_paths = sorted(args.results.rglob("*.jsonl"))
    if not result_paths:
        print(f"ERROR: no JSONL result files found under {args.results}")
        return 1

    failed = False
    manifest_entries: list[dict[str, Any]] = []
    for path in result_paths:
        records, errors = read_result_file(path)
        if errors:
            failed = True
            for error in errors:
                print(f"ERROR: {path}: {error}")
            continue

        result_ids = {record["id"] for _, record in records}
        missing_ids = ground_truth_ids - result_ids
        extra_ids = result_ids - ground_truth_ids
        if missing_ids:
            failed = True
            print(f"ERROR: {path}: missing {len(missing_ids)} GT IDs")
            continue

        if extra_ids and not args.normalize:
            failed = True
            print(f"ERROR: {path}: contains {len(extra_ids)} non-GT IDs")
            continue

        if extra_ids:
            kept_lines = [
                raw_line
                for raw_line, record in records
                if record["id"] in ground_truth_ids
            ]
            atomic_write_lines(path, kept_lines)
            print(f"NORMALIZED: {path}: removed {len(extra_ids)} non-GT rows")
            records, errors = read_result_file(path)
            if errors:
                failed = True
                for error in errors:
                    print(f"ERROR: {path}: {error}")
                continue

        manifest_entries.append(
            {
                "path": manifest_path(path),
                "record_count": len(records),
                "sha256": file_sha256(path),
            }
        )

    if failed:
        return 1

    output = {
        "schema_version": 1,
        "description": "Integrity metadata for bundled prediction files.",
        "dataset_release_id": DATASET_RELEASE_ID,
        "dataset_sorted_ids_sha256": EXPECTED_SORTED_IDS_SHA256,
        "result_file_count": len(manifest_entries),
        "files": manifest_entries,
    }
    if args.write_manifest is not None:
        args.write_manifest.write_text(
            json.dumps(output, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"WROTE: {args.write_manifest}")
    else:
        if not args.results_manifest.is_file():
            print(f"ERROR: result manifest not found: {args.results_manifest}")
            return 1
        with args.results_manifest.open("r", encoding="utf-8") as handle:
            expected_output = json.load(handle)
        if output != expected_output:
            print(
                f"ERROR: result hashes do not match {args.results_manifest}; "
                "review the changes and regenerate it explicitly with "
                "--write-manifest"
            )
            return 1

    print(
        f"OK: {len(manifest_entries)} result files match "
        f"{DATASET_RELEASE_ID}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
