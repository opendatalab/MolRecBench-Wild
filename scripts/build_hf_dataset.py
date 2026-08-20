"""Build the 2026-08-19 Hugging Face Parquet release and Dataset Card."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Iterator

import pyarrow.parquet as pq
import yaml
from datasets import Dataset, Features, Image, List, Value
from datasets.table import embed_table_storage


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ID = "2026-08-19"
EXPECTED_ROWS = 5024
EXPECTED_SUBSETS = {
    "A": 1987,
    "B": 1976,
    "C": 1061,
}
ATOM_FIELDS = (
    "charges",
    "radicals",
    "valences",
    "isotopes",
    "attach_points",
    "coords",
)


FEATURES = Features(
    {
        "image": Image(),
        "id": Value("string"),
        "release_id": Value("string"),
        "source": Value("string"),
        "source_doi": Value("string"),
        "source_url": Value("string"),
        "evaluation_subset": Value("string"),
        "hardcase_label": List(Value("string")),
        "symbols": List(Value("string")),
        "charges": List(Value("int64")),
        "radicals": List(Value("int64")),
        "valences": List(Value("int64")),
        "isotopes": List(Value("int64")),
        "attach_points": List(Value("int64")),
        "coords": List(List(Value("float64"))),
        "bonds": List(List(Value("int64"))),
        "brackets": List(
            {
                "alias": Value("string"),
                "atoms": List(Value("int64")),
                "display_rects": List(List(Value("float64"))),
            }
        ),
    }
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_doi(sample_id: str) -> str:
    parts = sample_id.split("_")
    if len(parts) < 2 or not parts[0].startswith("10."):
        raise ValueError(f"cannot derive DOI from sample ID: {sample_id}")
    return f"{parts[0]}/{parts[1]}"


def validate_record(record: dict[str, Any], image_dir: Path) -> None:
    sample_id = record.get("id")
    if not isinstance(sample_id, str) or not sample_id:
        raise ValueError("every record must have a non-empty string ID")
    image_path = image_dir / sample_id
    if not image_path.is_file():
        raise FileNotFoundError(f"missing image for {sample_id}: {image_path}")

    symbols = record.get("symbols")
    if not isinstance(symbols, list):
        raise ValueError(f"symbols must be a list for {sample_id}")
    atom_count = len(symbols)
    for field in ATOM_FIELDS:
        values = record.get(field)
        if not isinstance(values, list) or len(values) != atom_count:
            raise ValueError(f"{field} length does not match symbols for {sample_id}")

    for bond in record.get("bonds", []):
        if (
            not isinstance(bond, list)
            or len(bond) != 3
            or not all(isinstance(value, int) for value in bond)
            or not 0 <= bond[0] < atom_count
            or not 0 <= bond[1] < atom_count
        ):
            raise ValueError(f"invalid bond in {sample_id}: {bond!r}")

    for bracket in record.get("brackets", []):
        if set(bracket) != {"alias", "atoms", "display_rects"}:
            raise ValueError(f"invalid bracket fields in {sample_id}: {bracket!r}")
        if not isinstance(bracket["alias"], str) or any(
            not isinstance(atom_id, int) or not 0 <= atom_id < atom_count
            for atom_id in bracket["atoms"]
        ):
            raise ValueError(f"invalid bracket in {sample_id}: {bracket!r}")


def load_records(annotation_path: Path, image_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with annotation_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                validate_record(record, image_dir)
            except Exception as error:
                raise ValueError(
                    f"invalid annotation at line {line_number}: {error}"
                ) from error
            records.append(record)

    records.sort(key=lambda item: item["id"])
    ids = [record["id"] for record in records]
    if len(records) != EXPECTED_ROWS:
        raise ValueError(f"expected {EXPECTED_ROWS} records, found {len(records)}")
    if len(ids) != len(set(ids)):
        raise ValueError("annotation contains duplicate IDs")

    subset_counts = {
        subset: sum(record["evaluation_subset"] == subset for record in records)
        for subset in EXPECTED_SUBSETS
    }
    if subset_counts != EXPECTED_SUBSETS:
        raise ValueError(
            f"evaluation subset counts differ: {subset_counts} != {EXPECTED_SUBSETS}"
        )
    return records


def dataset_rows(
    records: list[dict[str, Any]], image_dir: Path
) -> Iterator[dict[str, Any]]:
    for record in records:
        doi = source_doi(record["id"])
        url = f"https://doi.org/{doi}"
        yield {
            "image": str(image_dir / record["id"]),
            "id": record["id"],
            "release_id": RELEASE_ID,
            "source": url,
            "source_doi": doi,
            "source_url": url,
            "evaluation_subset": record["evaluation_subset"],
            "hardcase_label": record["hardcase_label"],
            "symbols": record["symbols"],
            "charges": record["charges"],
            "radicals": record["radicals"],
            "valences": record["valences"],
            "isotopes": record["isotopes"],
            "attach_points": record["attach_points"],
            "coords": record["coords"],
            "bonds": record["bonds"],
            "brackets": record["brackets"],
        }


def dataset_card(front_matter: dict[str, Any]) -> str:
    yaml_header = yaml.safe_dump(
        front_matter,
        sort_keys=False,
        allow_unicode=True,
        width=1000,
    ).strip()
    return f"""---
{yaml_header}
---

# MolRecBench-Wild (`2026-08-19`)

MolRecBench-Wild is a real-world benchmark for optical chemical structure
recognition. This release contains **5,024** molecular structure images and
their CARBON molecular-graph annotations from **818** source articles.

This is the repository's authoritative `2026-08-19` release. It differs from the
5,029-sample snapshot described in the first arXiv version of the paper.

## Dataset structure

The dataset has one `test` split. Images are embedded in native Parquet files,
so the Hugging Face Dataset Viewer can display each image next to its structured
annotation.

```python
from datasets import load_dataset

dataset = load_dataset("opendatalab/MolRecBench-Wild", split="test")
sample = dataset[0]
sample["image"].show()
print(sample["id"], sample["symbols"], sample["bonds"])
```

### Fields

- `image`: cropped molecular structure image.
- `id`: stable sample identifier and original image filename.
- `release_id`: dataset release date (`2026-08-19`, ISO 8601 format).
- `source`, `source_doi`, `source_url`: provenance derived from the DOI encoded
  in the sample ID.
- `evaluation_subset`: benchmark difficulty subset (`A`, `B`, or `C`).
- `hardcase_label`: visual and chemical difficulty labels.
- `symbols`, `charges`, `radicals`, `valences`, `isotopes`, `attach_points`,
  `coords`, `bonds`, `brackets`: CARBON graph annotation fields.

Subset sizes are 1,987 `A` samples, 1,976 `B` samples, and 1,061 `C` samples.
Subset A has no specified chemical-semantic property difficulty labels and
relatively few visual difficulty labels; B has no such property labels but
more visual difficulty labels; C contains specified chemical-semantic property
difficulty labels.

## Source information

A DOI and resolver URL are included with every sample to identify its source
article. This Dataset Card does not declare a license for this release.

## Citation

Please cite the MolRecBench-Wild paper:

- *MolRecBench-Wild: A Real-World Benchmark for Optical Chemical Structure
  Recognition*, CVPR 2026, [arXiv:2605.05832](https://arxiv.org/abs/2605.05832).

## Release integrity

Checksums, row counts, Parquet shard metadata, and the image-set fingerprint are
available in `release_manifest.json`.
"""


def build_release(args: argparse.Namespace) -> None:
    annotation_path = args.annotation.resolve()
    image_dir = args.image_dir.resolve()
    output_dir = args.output.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"output directory is not empty: {output_dir}")
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    records = load_records(annotation_path, image_dir)
    with tempfile.TemporaryDirectory(prefix=".build-cache-", dir=output_dir) as cache:
        dataset = Dataset.from_generator(
            dataset_rows,
            features=FEATURES,
            gen_kwargs={"records": records, "image_dir": image_dir},
            cache_dir=cache,
            keep_in_memory=True,
            split="test",
        )

    shard_metadata: list[dict[str, Any]] = []
    for shard_index in range(args.num_shards):
        shard = dataset.shard(
            num_shards=args.num_shards,
            index=shard_index,
            contiguous=True,
        )
        shard = shard.with_format("arrow").map(
            embed_table_storage,
            batched=True,
            batch_size=args.row_group_size,
            keep_in_memory=True,
        )
        relative_path = f"data/test-{shard_index:05d}-of-{args.num_shards:05d}.parquet"
        shard_path = output_dir / relative_path
        shard.to_parquet(
            shard_path,
            batch_size=args.row_group_size,
            write_page_index=True,
        )
        parquet = pq.ParquetFile(shard_path)
        row_groups = parquet.metadata.num_row_groups
        max_rows = max(
            parquet.metadata.row_group(index).num_rows for index in range(row_groups)
        )
        if parquet.metadata.num_rows != len(shard):
            raise RuntimeError(f"row count mismatch in {relative_path}")
        if max_rows > args.row_group_size:
            raise RuntimeError(f"row group too large in {relative_path}: {max_rows}")
        first_image = parquet.read_row_group(0, columns=["image"])["image"][0].as_py()
        if not first_image.get("bytes"):
            raise RuntimeError(f"image bytes are not embedded in {relative_path}")
        if first_image.get("path") and Path(first_image["path"]).is_absolute():
            raise RuntimeError(f"image path is still absolute in {relative_path}")
        shard_metadata.append(
            {
                "path": relative_path,
                "rows": len(shard),
                "row_groups": row_groups,
                "max_rows_per_group": max_rows,
                "size_bytes": shard_path.stat().st_size,
                "sha256": sha256_file(shard_path),
            }
        )

    image_digest = hashlib.sha256()
    for record in records:
        image_path = image_dir / record["id"]
        image_digest.update(record["id"].encode("utf-8"))
        image_digest.update(b"\0")
        image_digest.update(sha256_file(image_path).encode("ascii"))
        image_digest.update(b"\n")

    release_manifest = {
        "schema_version": 1,
        "release_id": RELEASE_ID,
        "sample_count": len(records),
        "source_doi_count": len({source_doi(record["id"]) for record in records}),
        "annotation_jsonl_sha256": sha256_file(annotation_path),
        "image_set_sha256": image_digest.hexdigest(),
        "parquet_shards": shard_metadata,
    }
    (output_dir / "release_manifest.json").write_text(
        json.dumps(release_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    front_matter = {
        "language": ["en"],
        "pretty_name": "MolRecBench-Wild",
        "task_categories": ["image-to-text"],
        "tags": [
            "chemistry",
            "optical-chemical-structure-recognition",
            "molecular-graph",
            "carbon-notation",
        ],
        "size_categories": ["1K<n<10K"],
        "configs": [
            {
                "config_name": "default",
                "default": True,
                "data_files": [{"split": "test", "path": "data/test-*.parquet"}],
            }
        ],
        "dataset_info": {"features": FEATURES._to_yaml_list()},
    }
    (output_dir / "README.md").write_text(dataset_card(front_matter), encoding="utf-8")
    print(f"Built {len(records)} rows in {len(shard_metadata)} shards at {output_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--annotation",
        type=Path,
        default=REPO_ROOT / "dataset" / "annotation.jsonl",
    )
    parser.add_argument(
        "--image-dir", type=Path, default=REPO_ROOT / "dataset" / "images"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--num-shards", type=int, default=4)
    parser.add_argument("--row-group-size", type=int, default=100)
    return parser


if __name__ == "__main__":
    build_release(build_parser().parse_args())
