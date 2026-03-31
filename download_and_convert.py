"""
Download U-MolRecBench-Wild dataset from HuggingFace and convert to TSV format for VLMEvalKit inference.

Usage:
    python download_and_convert.py --prompt smiles          # SMILES track (default)
    python download_and_convert.py --prompt graph_simple    # Simplified Graph track
    python download_and_convert.py --prompt graph           # Full CARBON Graph track
    python download_and_convert.py --prompt all             # All tracks at once
    python download_and_convert.py --prompt smiles -n 100   # Only first 100 samples
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import jsonlines
from datasets import load_dataset
from huggingface_hub import login
from PIL import Image
from tqdm import tqdm

DATASET_NAME = "opendatalab/U-MolRecBench-Wild"
SAVE_PATH = "./dataset"
IMAGE_PATH = "./dataset/images"
LMUDATA_PATH = os.path.expanduser("~/LMUData")

PROMPT_DIR = Path(__file__).parent / "inference" / "scripts" / "chem" / "prompt"
PROMPT_MAP = {
    "smiles": ("smiles.txt", "chem_smiles"),
    "graph_simple": ("graph_simple.txt", "chem_graph_simple"),
    "graph": ("graph.txt", "chem"),
}


def encode_image_to_base64(image: Image.Image) -> str:
    import base64
    import io
    buffer = io.BytesIO()
    fmt = image.format or "PNG"
    image.save(buffer, format=fmt)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def download_dataset():
    """Download dataset from HuggingFace, save images and annotation JSONL."""
    HF_TOKEN = os.environ.get("HF_TOKEN", None)
    if HF_TOKEN:
        login(HF_TOKEN)
    else:
        login()

    os.makedirs(SAVE_PATH, exist_ok=True)
    os.makedirs(IMAGE_PATH, exist_ok=True)

    dataset = load_dataset(DATASET_NAME, split="test")

    annotation = []
    for idx, row in tqdm(enumerate(dataset), desc="Downloading images", total=len(dataset)):
        image = row["image"]
        sample_id = row["id"]
        image_path = os.path.join(IMAGE_PATH, sample_id)
        image.save(image_path)

        carbon_info = {
            "id": sample_id,
            "image_path": image_path,
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
        }
        annotation.append(carbon_info)

    annotation_path = os.path.join(SAVE_PATH, "annotation.jsonl")
    with jsonlines.open(annotation_path, "w") as writer:
        for item in annotation:
            writer.write(item)

    print(f"Downloaded {len(annotation)} samples to {SAVE_PATH}/")
    return annotation_path


def convert_to_tsv(annotation_path, prompt_name, num_samples=None):
    """Convert annotation JSONL to VLMEvalKit TSV format using the specified prompt."""
    prompt_file, tsv_name = PROMPT_MAP[prompt_name]
    prompt_path = PROMPT_DIR / prompt_file

    with open(prompt_path, "r", encoding="utf-8") as f:
        question_text = f.read().strip()

    os.makedirs(LMUDATA_PATH, exist_ok=True)
    output_tsv = os.path.join(LMUDATA_PATH, f"{tsv_name}.tsv")

    rows = []
    with open(annotation_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            if num_samples is not None and len(rows) >= num_samples:
                break

            data = json.loads(line.strip())
            image_path = data.get("image_path", "")
            if not image_path or not os.path.exists(image_path):
                continue

            img = Image.open(image_path)
            image_base64 = encode_image_to_base64(img)

            rows.append({
                "index": data.get("id", ""),
                "image": image_base64,
                "image_url": image_path,
                "question": question_text,
                "answer": "",
            })

    if rows:
        with open(output_tsv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["index", "image", "image_url", "question", "answer"],
                delimiter="\t",
                quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    print(f"[{prompt_name}] Converted {len(rows)} samples -> {output_tsv}")


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
        "-n", "--num-samples",
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

    annotation_path = os.path.join(SAVE_PATH, "annotation.jsonl")
    if args.skip_download and os.path.exists(annotation_path):
        print(f"Skipping download, using existing {annotation_path}")
    else:
        annotation_path = download_dataset()

    prompts = list(PROMPT_MAP.keys()) if args.prompt == "all" else [args.prompt]
    for p in prompts:
        convert_to_tsv(annotation_path, p, args.num_samples)


if __name__ == "__main__":
    main()
