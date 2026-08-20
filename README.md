<p align="center">
  <img src="assets/banner.png" width="45%" alt="Open Data Lab" />
</p>

<h1 align="center">MolRecBench-Wild</h1>

<p align="center">
  <b>A Real-World Benchmark for Optical Chemical Structure Recognition</b>
</p>

<p align="center">
  <a href="https://arxiv.org/abs/2605.05832"><img src="https://img.shields.io/badge/arXiv-2605.05832-b31b1b.svg" alt="arXiv"></a>
  <a href="https://openaccess.thecvf.com/content/CVPR2026F/html/Yang_MolRecBench-Wild_A_Real-World_Benchmark_for_Optical_Chemical_Structure_Recognition_CVPRF_2026_paper.html"><img src="https://img.shields.io/badge/CVPR%202026-Open%20Access-blue.svg" alt="CVPR 2026 Open Access"></a>
  <a href="https://arxiv.org/abs/2608.03525"><img src="https://img.shields.io/badge/Technical%20Report-arXiv%202608.03525-b31b1b.svg" alt="MinerU.Chem Technical Report"></a>
  <a href="https://huggingface.co/datasets/opendatalab/MolRecBench-Wild"><img src="https://img.shields.io/badge/🤗%20Dataset-MolRecBench--Wild-blue" alt="Dataset"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/Code%20License-Apache%202.0-green.svg" alt="Code License"></a>

</p>

<p align="center">
  <a href="README_zh.md">🇨🇳 中文文档</a>
</p>

<p align="center">
  <img src="assets/why_molrecbench_wild.png" width="50%" alt="Why Molrecbench Wild" />
</p>

## 🔥 News

- 🚀 [2026-05-07] MolRecBench-Wild v1 was released on [arXiv](https://arxiv.org/abs/2605.05832).

## 📊 Dataset Statistics

| Item | Current repository release |
| :--- | :--- |
| **Release** | `2026-08-19` |
| **Source** | Molecular structure figures from academic articles |
| **Sample count** | 5,024 |
| **Ground truth** | CARBON molecular graph annotations |
| **Difficulty metadata** | `hardcase_label` (50 distinct values in the `2026-08-19` release) |
| **Evaluation subsets** | A: 1,987; B: 1,976; C: 1,061 |
| **Evaluation tracks** | SMILES, Simplified Graph, and Graph |

The arXiv v1 paper describes an earlier 5,029-sample snapshot. This repository
uses the 5,024-sample `2026-08-19` release as its authoritative ground truth.

## Repository Layout

```text
.
├── assets/                  README images
├── evaluate/                Evaluation package (`python -m evaluate`)
├── patches/                 Pinned VLMEvalKit integration patch
├── prompts/                 Track prompts and visual examples
├── results/                 Bundled prediction JSONL files
│   └── manifest.json         Integrity metadata for bundled results
└── scripts/                 Setup, conversion, validation, and release tools
```

`dataset/`, `LMUData/`, and `VLMEvalKit/` are generated at runtime and are not
version-controlled.


## CARBON Notation

<p align="center">
  <img src="assets/10.1002_anie.202405775_8_figure_1_mol_2.jpg" width="45%" alt="Example Image" />
</p>


```json
{
  "symbols": ["[R]", "C", "[R']", "C", "C", "H", "C", "[Ar]", "C", "C"], 
  "charges": [null, null, null, null, null, null, null, null, null, null], 
  "radicals": [null, null, null, null, null, null, null, null, null, null], 
  "valences": [null, null, null, null, null, null, null, null, null, null], 
  "isotopes": [null, null, null, null, null, null, null, null, null, null], 
  "attach_points": [null, null, null, null, null, null, null, null, null, null], 
  "coords": [
      [10.8075, -9.3566], 
      [11.7673, -9.3302], 
      [11.4253, -10.2699], 
      [12.6333, -9.8302], 
      [13.4993, -9.3302], 
      [14.3654, -9.8302], 
      [13.4993, -8.3302], 
      [14.3654, -7.8302], 
      [12.6333, -7.8302], 
      [11.7673, -8.3302]
    ], 
  "bonds": [
      [0, 1, 1], 
      [1, 2, 1], 
      [1, 3, 1], 
      [1, 9, 7], 
      [3, 4, 1], 
      [4, 5, 1], 
      [4, 6, 2], 
      [6, 7, 1], 
      [6, 8, 1], 
      [8, 9, 7]
    ], 
  "brackets": [
      {
        "alias": "n", 
        "atoms": [3], 
        "display_rects": [
            [11.9503, -10.0132, 12.4503, -9.1472], 
            [12.8163, -9.1472, 13.3163, -10.0132]
          ]
      }
      ]
}
```

## ⚡ Quick Start

### Step 1: Setup Environment

```bash
git clone https://github.com/opendatalab/MolRecBench-Wild.git
cd MolRecBench-Wild

# Create and activate the environment, then install dependencies
conda create -n molrec python=3.10 -y
conda activate molrec
python -m pip install -r requirements.txt
```

### Step 2: Setup VLMEvalKit

We use [VLMEvalKit](https://github.com/open-compass/VLMEvalKit) as the inference
backend. The setup script checks out the pinned upstream commit
`b9ff66c970449a8106c02570102bcfb2fb3df462` and applies the chemistry integration
patch in [`patches/`](patches/). VLMEvalKit itself is obtained from upstream and
is not redistributed in this repository.

Run the one-click setup script:

```bash
bash scripts/setup_vlmevalkit.sh
```

For API-backed models, add the credentials required by the selected adapter to
`VLMEvalKit/.env`. Local model adapters do not require the OpenAI variables
shown below. Never commit this file.

```bash
# VLMEvalKit/.env
OPENAI_API_BASE=https://your-api-base-url
OPENAI_API_KEY=your-api-key
```

### Step 3: Download & Convert Data

Download the dataset from HuggingFace and convert it to VLMEvalKit TSV format in one step:

```bash
# Download the dataset and generate TSV files for all three tracks
python scripts/download_and_convert_dataset.py --prompt all

# Download dataset and convert to SMILES track TSV
python scripts/download_and_convert_dataset.py --prompt smiles

# Reuse a previously downloaded dataset
python scripts/download_and_convert_dataset.py --prompt smiles --skip-download
```

The script will:

1. Download images to `./dataset/images/` and save ground truth to `./dataset/annotation.jsonl`
2. Generate TSV files to `./LMUData/`
3. Automatically register the `LMUData` path in `VLMEvalKit/.env` so VLMEvalKit can find the TSV files

The downloader is pinned to the immutable Hugging Face `2026-08-19` release revision
`e8999662272ee5a9fd565e5dabf28feb12962dee`. It validates the 5,024 IDs,
required annotation fields, evaluation-subset counts, atom-field lengths, and
local image presence before conversion.

### Step 4: Run Inference

```bash
cd VLMEvalKit

# Run a single task (SMILES)
python run.py --data chem_smiles --model GPT4o_20241120

# Run all three tasks at once (SMILES, Simplified Graph, Graph)
python run.py --data chem_smiles chem_graph_simple chem_graph --model GPT4o_20241120

# Increase parallel API calls for faster inference
python run.py --data chem_smiles --model GPT4o_20241120 --api-nproc 32

# Resume an interrupted run (skip already completed samples)
python run.py --data chem_smiles --model GPT4o_20241120 --reuse
```

**Key arguments:**

| Argument | Description |
| :--- | :--- |
| `--data` | Dataset ID to run: `chem_smiles`, `chem_graph_simple`, or `chem_graph` |
| `--model` | Model name as defined in `vlmeval/config.py` |
| `--work-dir` | Output directory (default: `./outputs`) |
| `--api-nproc` | Number of parallel API calls (default: 4, increase for faster inference) |
| `--reuse` | Reuse existing prediction files to resume interrupted runs |

Prediction results will be saved to `VLMEvalKit/outputs/<model_name>/`.

**Testing with your own model:**

To evaluate a custom model, implement a VLMEvalKit model wrapper. At minimum,
create a class with a `generate_inner(msgs, dataset=None)` method that accepts a
multimodal message list and returns the prediction string, then register it in
`vlmeval/config.py`. See the [development guide for the pinned upstream
commit](https://github.com/open-compass/VLMEvalKit/blob/b9ff66c970449a8106c02570102bcfb2fb3df462/docs/en/Development.md#implement-a-new-model).

### Step 5: Prepare Prediction JSONL

Return to the repository root after inference:

```bash
cd ..
```

The evaluator consumes one JSON object per line. Every prediction must use the
exact `id` from `dataset/annotation.jsonl`. A SMILES prediction requires at
least `id` and `smiles`; graph predictions use the CARBON fields shown above.

Convert a VLMEvalKit workbook by selecting the track explicitly:

```bash
python scripts/convert_result.py \
  --input "VLMEvalKit/outputs/<model>/<run-id>/<prediction>.xlsx" \
  --output "local_results/<model>_graph.jsonl" \
  --track graph \
  --strict-predictions \
  --errors-output "/tmp/<model>_graph_errors.jsonl"
```

The dataset-to-track mapping is `chem_smiles` → `smiles`,
`chem_graph_simple` → `s_graph`, and `chem_graph` → `graph`. Text filename IDs,
including the current `.jpg` IDs, keep their values by default; surrounding
whitespace is stripped and numeric cells are normalized. Use `--id-suffix
.jpg` only for a legacy workbook whose IDs omit that suffix. A workbook with
multiple sheets must be resolved with `--sheet NAME` or the explicit
`--all-sheets` merge mode; IDs must be unique across all merged sheets. For
historical CARBON attachment-point predictions, `atom1` is the retained atom
and `atom2` is the dummy atom removed during conversion. Malformed predictions
retain their IDs as empty predictions; `--strict-predictions` prevents the
output from being replaced when any such error is found.

To enforce exact 5,024-ID coverage for a directory of custom JSONL files, run:

```bash
python scripts/validate_results.py \
  --results local_results \
  --write-manifest /tmp/local_results_manifest.json
```

### Step 6: Evaluation

After inference, use the Evaluator to compute accuracy on three tracks. The Evaluator takes two JSONL files — ground truth and predictions.

**Evaluation metrics:**

| Metric | What it compares | Description |
| :--- | :--- | :--- |
| **SMILES Accuracy** | Canonical SMILES | Scores only SMILES-eligible GT records after CARBON conversion and abbreviation expansion. It compares exact canonical SMILES, ignoring double-bond cis/trans by default while retaining atom chirality. |
| **Simplified Graph Accuracy** | Symbols + simplified bond types | Directed graph isomorphism after symbol and bond simplification. Chemical atom attributes, attachment points, brackets, and coordinates are ignored. |
| **Graph Accuracy** | CARBON chemical attributes | Directed graph isomorphism over symbols, charge, radical, valence, isotope, attachment points, bonds, and bracket alias/atom membership. Coordinates and bracket display rectangles are not compared. |

**Running evaluation:**

```bash
python -m evaluate smiles \
  --gt-path dataset/annotation.jsonl \
  --pred-path results/MLLM/GPT-5.6-sol/GPT-5.6-sol_smiles.jsonl \
  --output-csv eval_results/GPT-5.6-sol/GPT-5.6-sol_smiles_eval.csv \
  --missing-abbreviations-output vis_results/miss_abbr.csv
# Current result: 1,791 / 2,392 eligible GT = 0.7487458194

python -m evaluate s_graph \
  --gt-path dataset/annotation.jsonl \
  --pred-path results/MLLM/GPT-5.6-sol/GPT-5.6-sol_graph_simple.jsonl
# Current result: 1,828 / 5,024 GT = 0.3638535032

python -m evaluate graph \
  --gt-path dataset/annotation.jsonl \
  --pred-path results/MLLM/GPT-5.6-sol/GPT-5.6-sol_graph.jsonl
# Current result: 1,636 / 5,024 GT = 0.3256369427
```

SMILES evaluation ignores double-bond cis/trans slash directions by default,
matching the benchmark protocol. Atom chirality (`@`/`@@`) is always compared.
Use `--preserve-cistrans` to compare both forms of stereochemistry.

Evaluation requires complete, unique prediction-ID coverage by default.
Missing IDs, IDs outside the full GT, duplicate IDs, malformed rows, and rows
without a string ID stop the evaluation. When using `--limit` or `--split`,
predictions for non-selected GT records are allowed, but every selected GT ID
must be present. Use `--allow-coverage-mismatch` only for intentionally partial
ID-coverage diagnostics; malformed JSON remains invalid for Graph tracks.

To verify that repository result files cover all 5,024 GT IDs, run:

```bash
python scripts/validate_results.py
```

To evaluate every supported JSONL below `results/` and write the consolidated
paper-style Excel table, run:

```bash
python -m evaluate.eval_all --timeout 0
# Default output: results/evaluation_results.xlsx
```

`--timeout 0` disables the per-record graph-isomorphism timeout and is the
setting used for the table below; it can take longer but avoids small
platform-dependent timeout differences. The default timeout is five seconds.
Use `--output`, `--include`, or `--exclude` to customize the output path or
select files. `--limit` and `--max-files` are available for smoke tests.
Batch evaluation applies the same strict ID-coverage policy; pass
`--allow-coverage-mismatch` only when partial files are expected.

Each record in `dataset/annotation.jsonl` contains an `evaluation_subset`
field. The paper-table mapping is:

- A: no specified chemical-semantic property difficulty labels and relatively
  few visual difficulty labels (1,987 records)
- B: no specified chemical-semantic property difficulty labels but more visual
  difficulty labels (1,976 records)
- C: contains specified chemical-semantic property difficulty labels (1,061 records)

The stored `evaluation_subset` values are the literal strings `A`, `B`, and
`C`, following the definitions in
[MinerU.Chem](https://arxiv.org/abs/2608.03525).

## Benchmark Results

The repository contains 34 prediction JSONL files covering 17 systems. The
values below are exact-match accuracies (%) recomputed with the current
evaluator against release `2026-08-19`, using `--timeout 0`. The SMILES denominators are
2,392 for Full, 1,219 for A, 875 for B, and 298 for C. The Graph denominators
are 5,024 for Full, 1,987 for A, 1,976 for B, and 1,061 for C. A dash means that
the corresponding prediction file is not included. These values are not
directly comparable to the earlier 5,029-sample results in arXiv v1.

| Method | Full SMILES | Full Graph | A SMILES | A Graph | B SMILES | B Graph | C SMILES | C Graph |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OCSU | 11.41 | — | 14.60 | — | 9.03 | — | 5.37 | — |
| DECIMER v2.2 | 41.43 | — | 60.21 | — | 22.97 | — | 18.79 | — |
| MolGrapher | 34.78 | — | 47.01 | — | 27.77 | — | 5.37 | — |
| MolNexTR | 62.50 | — | 76.78 | — | 52.11 | — | 34.56 | — |
| MolScribe | 62.29 | — | 77.28 | — | 50.97 | — | 34.23 | — |
| ChemDFM-X | 19.06 | — | 25.18 | — | 13.94 | — | 9.06 | — |
| ChemVLM | 8.03 | — | 11.07 | — | 5.94 | — | 1.68 | — |
| Logic-Parsing | 25.84 | — | 33.39 | — | 21.49 | — | 7.72 | — |
| Mathpix | 47.32 | — | 58.65 | — | 41.03 | — | 19.46 | — |
| InternVL3.5 | 39.80 | 3.01 | 46.92 | 4.73 | 34.86 | 2.13 | 25.17 | 1.41 |
| GLM-4.5V | 20.28 | 4.20 | 24.53 | 7.15 | 18.17 | 2.94 | 9.06 | 1.04 |
| Intern-S1 | 30.02 | 3.46 | 36.10 | 5.89 | 25.26 | 2.13 | 19.13 | 1.41 |
| Seed1.6-Thinking | 24.83 | 4.62 | 30.19 | 7.15 | 19.77 | 3.44 | 17.79 | 2.07 |
| Claude-opus-4-8 | 65.47 | 14.29 | 72.85 | 21.24 | 61.49 | 11.44 | 46.98 | 6.60 |
| Gemini-3.5-flash-thinking | 66.85 | 37.56 | 72.03 | 50.73 | 62.97 | 31.93 | 57.05 | 23.37 |
| GPT-5.6-Sol | 74.87 | 32.56 | 81.95 | 44.44 | 70.06 | 28.14 | 60.07 | 18.57 |
| **MinerU.Chem (GTR-VL-1.4.13)** | **93.02** | **79.66** | **98.28** | **92.15** | **93.49** | **80.11** | **70.13** | **55.42** |

## Citation

If you use MolRecBench-Wild, the MOSAIC framework, or the CARBON notation in your research, please cite our [CVPR 2026 paper](https://openaccess.thecvf.com/content/CVPR2026F/html/Yang_MolRecBench-Wild_A_Real-World_Benchmark_for_Optical_Chemical_Structure_Recognition_CVPRF_2026_paper.html) (also available on [arXiv](https://arxiv.org/abs/2605.05832)). The accompanying [MinerU.Chem technical report](https://arxiv.org/abs/2608.03525) describes the updated benchmark release and system results:

```bibtex
@inproceedings{yang2026molrecbench,
  title={MolRecBench-Wild: A Real-World Benchmark for Optical Chemical Structure Recognition},
  author={Yang, Haote and Wang, Hui and Zhu, Chen and Wang, Jingchao and Li, Linye and Lai, Hongbin and Ao, Huijie and Lyu, Yongxuan and Wu, Jiang and Sun, Jiaxing and Chen, Lua and Cao, Yuanyuan and Zhang, Ruijie and Lu, Shengxin and Wu, Lijun and Wang, Bin and He, Conghui},
  booktitle={Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition},
  year={2026}
}
```

## License

Original project source code is licensed under the Apache License 2.0; see
[`LICENSE`](LICENSE). This license does not automatically
cover dataset images or annotations, model weights, prediction outputs,
third-party software, or third-party assets. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and the applicable upstream
terms before use or redistribution.
