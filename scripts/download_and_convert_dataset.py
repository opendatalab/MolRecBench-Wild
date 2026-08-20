"""
Download U-MolRecBench-Wild dataset from HuggingFace and convert to TSV format for VLMEvalKit inference.

Usage:
    python scripts/download_and_convert_dataset.py --prompt smiles
    python scripts/download_and_convert_dataset.py --prompt graph_simple
    python scripts/download_and_convert_dataset.py --prompt graph
    python scripts/download_and_convert_dataset.py --prompt all
    python scripts/download_and_convert_dataset.py --prompt smiles -n 100
"""

import argparse
import csv
import json
import os
import re
import tempfile
from pathlib import Path

import jsonlines
from datasets import load_dataset
from PIL import Image
from tqdm import tqdm

DATASET_NAME = "opendatalab/MolRecBench-Wild"
DATASET_REVISION = "e8999662272ee5a9fd565e5dabf28feb12962dee"
DATASET_SPLIT = "test"
EXPECTED_SAMPLE_COUNT = 5024
EXPECTED_SUBSET_COUNTS = {
    "A": 1987,
    "B": 1976,
    "C": 1061,
}
REQUIRED_FIELDS = (
    "id",
    "evaluation_subset",
    "hardcase_label",
    "symbols",
    "charges",
    "radicals",
    "valences",
    "isotopes",
    "attach_points",
    "coords",
    "bonds",
    "brackets",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SAVE_PATH = REPO_ROOT / "dataset"
IMAGE_PATH = SAVE_PATH / "images"
LMUDATA_PATH = REPO_ROOT / "LMUData"
VLMEVALKIT_ENV = REPO_ROOT / "VLMEvalKit" / ".env"

PROMPT_DIR = REPO_ROOT / "prompts"
PROMPT_MAP = {
    "smiles": ("smiles.txt", "chem_smiles"),
    "graph_simple": ("graph_simple.txt", "chem_graph_simple"),
    "graph": ("graph.txt", "chem_graph"),
}
VISUAL_EXAMPLE_MAP = {
    "graph": ("visual_example.png", "cases.png"),
}


def encode_image_to_base64(image: Image.Image) -> str:
    import base64
    import io

    buffer = io.BytesIO()
    fmt = image.format or "PNG"
    image.save(buffer, format=fmt)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def validate_annotations(annotation: list[dict], *, require_images: bool) -> None:
    """Validate the fixed 2026-08-19 release used by this repository."""

    if len(annotation) != EXPECTED_SAMPLE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_SAMPLE_COUNT} annotations, found {len(annotation)}"
        )

    ids: set[str] = set()
    subset_counts = {name: 0 for name in EXPECTED_SUBSET_COUNTS}
    for row_number, record in enumerate(annotation, start=1):
        missing_fields = [field for field in REQUIRED_FIELDS if field not in record]
        if missing_fields:
            raise RuntimeError(
                f"Annotation row {row_number} is missing fields: "
                + ", ".join(missing_fields)
            )
        sample_id = record["id"]
        if not isinstance(sample_id, str) or not sample_id:
            raise RuntimeError(f"Annotation row {row_number} has an invalid id")
        if sample_id in ids:
            raise RuntimeError(f"Duplicate annotation id: {sample_id!r}")
        ids.add(sample_id)

        subset = record["evaluation_subset"]
        if subset not in subset_counts:
            raise RuntimeError(
                f"Annotation {sample_id!r} has an unknown evaluation_subset: {subset!r}"
            )
        subset_counts[subset] += 1

        atom_count = len(record["symbols"])
        for field in (
            "charges",
            "radicals",
            "valences",
            "isotopes",
            "attach_points",
            "coords",
        ):
            if len(record[field]) != atom_count:
                raise RuntimeError(
                    f"Annotation {sample_id!r} has {len(record[field])} {field} "
                    f"values for {atom_count} atoms"
                )
        if require_images and not (IMAGE_PATH / sample_id).is_file():
            raise RuntimeError(f"Image is missing for annotation {sample_id!r}")

    if subset_counts != EXPECTED_SUBSET_COUNTS:
        raise RuntimeError(
            f"Unexpected evaluation subset counts: {subset_counts}; "
            f"expected {EXPECTED_SUBSET_COUNTS}"
        )


def load_local_annotations(annotation_path: Path) -> list[dict]:
    annotation: list[dict] = []
    with annotation_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"{annotation_path}:{line_number}: invalid JSON: {exc}"
                ) from exc
            if not isinstance(record, dict):
                raise RuntimeError(
                    f"{annotation_path}:{line_number}: record is not an object"
                )
            annotation.append(record)
    return annotation


def download_dataset():
    """Download dataset from HuggingFace, save images and annotation JSONL."""
    hf_token = os.environ.get("HF_TOKEN") or None

    dataset = load_dataset(
        DATASET_NAME,
        split=DATASET_SPLIT,
        revision=DATASET_REVISION,
        token=hf_token,
    )

    annotation = []
    for row in tqdm(dataset, desc="Validating annotations", total=len(dataset)):
        sample_id = row["id"]
        image_path = IMAGE_PATH / sample_id

        carbon_info = {
            "id": sample_id,
            "image_path": str(image_path),
            "evaluation_subset": row["evaluation_subset"],
            "hardcase_label": row["hardcase_label"],
            "symbols": row["symbols"],
            "charges": row["charges"],
            "radicals": row["radicals"],
            "valences": row["valences"],
            "isotopes": row["isotopes"],
            "attach_points": row["attach_points"],
            "coords": row["coords"],
            "bonds": row["bonds"],
            "brackets": row["brackets"],
            "source": row.get("source"),
        }
        annotation.append(carbon_info)

    validate_annotations(annotation, require_images=False)

    SAVE_PATH.mkdir(parents=True, exist_ok=True)
    IMAGE_PATH.mkdir(parents=True, exist_ok=True)
    for row in tqdm(dataset, desc="Saving images", total=len(dataset)):
        image_path = IMAGE_PATH / row["id"]
        row["image"].save(str(image_path))

    validate_annotations(annotation, require_images=True)

    annotation_path = SAVE_PATH / "annotation.jsonl"
    with jsonlines.open(str(annotation_path), "w") as writer:
        for item in annotation:
            writer.write(item)

    print(f"Downloaded {len(annotation)} samples to {SAVE_PATH}/")
    return str(annotation_path)


def convert_to_tsv(annotation_path, prompt_name, num_samples=None):
    """Convert annotation JSONL to VLMEvalKit TSV format using the specified prompt."""
    prompt_file, tsv_name = PROMPT_MAP[prompt_name]
    prompt_path = PROMPT_DIR / prompt_file

    with open(prompt_path, "r", encoding="utf-8") as f:
        question_text = f.read().strip()

    visual_examples = []
    for example_file in VISUAL_EXAMPLE_MAP.get(prompt_name, ()):
        example_path = PROMPT_DIR / example_file
        if not example_path.is_file():
            raise FileNotFoundError(f"Visual example does not exist: {example_path}")
        visual_examples.append(str(example_path))

    LMUDATA_PATH.mkdir(parents=True, exist_ok=True)
    output_tsv = LMUDATA_PATH / f"{tsv_name}.tsv"

    rows = []
    with open(annotation_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            if num_samples is not None and len(rows) >= num_samples:
                break

            data = json.loads(line.strip())
            image_path = data.get("image_path", "")
            if not image_path:
                sample_id = data.get("id", "")
                if sample_id:
                    image_path = str(IMAGE_PATH / sample_id)
            if not image_path or not os.path.exists(image_path):
                raise FileNotFoundError(
                    f"Image does not exist for annotation {data.get('id')!r}: "
                    f"{image_path}"
                )

            img = Image.open(image_path)
            image_base64 = encode_image_to_base64(img)

            rows.append(
                {
                    "index": data.get("id", ""),
                    "image": image_base64,
                    "image_url": image_path,
                    "question": question_text,
                    "answer": "",
                    **{
                        f"visual_example_{idx}": visual_example
                        for idx, visual_example in enumerate(
                            visual_examples, start=1
                        )
                    },
                }
            )

    expected_rows = EXPECTED_SAMPLE_COUNT if num_samples is None else min(
        num_samples, EXPECTED_SAMPLE_COUNT
    )
    if len(rows) != expected_rows:
        raise RuntimeError(
            f"Expected {expected_rows} TSV rows for {prompt_name}, found {len(rows)}"
        )

    with open(output_tsv, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["index", "image", "image_url", "question", "answer"]
        fieldnames.extend(
            f"visual_example_{idx}"
            for idx in range(1, len(visual_examples) + 1)
        )
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter="\t",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[{prompt_name}] Converted {len(rows)} samples -> {output_tsv}")


def update_vlmevalkit_env():
    """Write LMUData path to VLMEvalKit/.env so VLMEvalKit can find the TSV files."""
    lmudata_abs = str(LMUDATA_PATH)
    env_line = f"LMUData={lmudata_abs}"

    if VLMEVALKIT_ENV.is_symlink():
        raise RuntimeError(f"Refusing to replace symlink: {VLMEVALKIT_ENV}")

    if VLMEVALKIT_ENV.exists():
        content = VLMEVALKIT_ENV.read_text(encoding="utf-8")
        if re.search(r"^LMUData=", content, re.MULTILINE):
            content = re.sub(
                r"^LMUData=.*$", env_line, content, flags=re.MULTILINE
            )
        else:
            content = content.rstrip("\n") + "\n" + env_line + "\n"
    else:
        content = env_line + "\n"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=VLMEVALKIT_ENV.parent,
            prefix=f".{VLMEVALKIT_ENV.name}.",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            os.fchmod(temp_file.fileno(), 0o600)
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, VLMEVALKIT_ENV)
        os.chmod(VLMEVALKIT_ENV, 0o600)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise

    print(f"Registered LMUData={lmudata_abs} in {VLMEVALKIT_ENV}")


def main():
    parser = argparse.ArgumentParser(
        description="Download U-MolRecBench-Wild and convert to VLMEvalKit TSV format."
    )
    parser.add_argument(
        "--prompt",
        choices=["smiles", "graph_simple", "graph", "all"],
        default="smiles",
        help="Which prompt/track to use (default: smiles)",
    )
    parser.add_argument(
        "-n",
        "--num-samples",
        type=int,
        default=None,
        help="Only convert first N samples (default: all)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download if dataset/ already exists",
    )
    args = parser.parse_args()
    if args.num_samples is not None and args.num_samples < 0:
        parser.error("--num-samples must be non-negative")

    annotation_path = str(SAVE_PATH / "annotation.jsonl")
    if args.skip_download and os.path.exists(annotation_path):
        local_annotation = load_local_annotations(Path(annotation_path))
        validate_annotations(local_annotation, require_images=True)
        print(f"Skipping download, using validated {annotation_path}")
    else:
        annotation_path = download_dataset()

    prompts = list(PROMPT_MAP.keys()) if args.prompt == "all" else [args.prompt]
    for p in prompts:
        convert_to_tsv(annotation_path, p, args.num_samples)

    update_vlmevalkit_env()


if __name__ == "__main__":
    main()
