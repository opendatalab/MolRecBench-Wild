<p align="center">
  <img src="assets/banner.png" width="45%" alt="Open Data Lab" />
</p>

<h1 align="center">MolRecBench-Wild</h1>

<p align="center">
  <b>A Real-World Benchmark for Optical Chemical Structure Recognition</b>
</p>

<p align="center">
  <!-- <a href="https://arxiv.org/abs/2511.02384"><img src="https://img.shields.io/badge/arXiv-2511.02384-b31b1b.svg" alt="arXiv"></a> -->
  <a href="https://huggingface.co/datasets/opendatalab/MolRecBench-Wild"><img src="https://img.shields.io/badge/🤗%20Dataset-MolRecBench--Wild-blue" alt="Dataset"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-green.svg" alt="License"></a>

</p>

<p align="center">
  <a href="README_zh.md">🇨🇳 中文文档</a>
</p>

<p align="center">
  <img src="assets/why_molrecbench_wild.png" width="50%" alt="Why Molrecbench Wild" />
</p>

## 🔥 News

- 🚀 [04/07/2026] Our paper is accepted by **CVPRF 2026**!

## 📊 Dataset Statistics

| Feature | MolRecBench-Wild | Traditional Benchmarks (e.g., USPTO, Staker) |
| :--- | :--- | :--- |
| **Source** | Academic Articles | Patents / Synthetic |
| **Sample Count** | 5029 | Varies (usually larger but simpler) |
| **Visual Difficulty Labels** | 18 Categories | < 10 Categories |
| **Chemical Difficulty Labels** | 19 Categories (MOSAIC subset) | < 3 Categories |
| **Ground Truth** | CARBON, Graph, SMILES | SMILES, MolFile |
| **Complex Structure Support** | Non-standard bonds, icon groups, mixed valences | Standard structures only |


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

### Step 1:  Setup Environment

```bash
git clone https://github.com/your-username/MolRecBench-Wild.git
cd MolRecBench-Wild

# Install dependencies
conda create -n molrec python=3.10 -y
pip install -r requirements.txt
```

### Step 2: Setup VLMEvalKit

We use [VLMEvalKit](https://github.com/open-compass/VLMEvalKit) as the inference backend, with minimal patches to add chemistry-specific model adapters and datasets. Our patches are provided in [`patches/`](./patches/) for full transparency — we do not redistribute VLMEvalKit itself.

Run the one-click setup script:

```bash
bash setup_vlmevalkit.sh
```

After setup, create a file named ".env" in the VLMEvalKit directory and configure your API keys:

```bash
# VLMEvalKit/.env
OPENAI_API_BASE=https://your-api-base-url
OPENAI_API_KEY=your-api-key
```

### Step 3: Download & Convert Data

Download the dataset from HuggingFace and convert it to VLMEvalKit TSV format in one step:

```bash
# Defaulit: download all tracks data
python download_and_convert.py --prompt all             # generate TSV for all three tracks

# Download dataset and convert to SMILES track TSV
python download_and_convert.py --prompt smiles

python download_and_convert.py --prompt smiles --skip-download  # skip download if dataset/ already exists
```

The script will:
1. Download images to `./dataset/images/` and save ground truth to `./dataset/annotation.jsonl`
2. Generate TSV files to `./LMUData/`
3. Automatically register the `LMUData` path in `VLMEvalKit/.env` so VLMEvalKit can find the TSV files

### Step 4: Run Inference

```bash
cd VLMEvalKit

# Run a single task (SMILES)
python run.py --data smiles --model GPT4o_20241120

# Run all three tasks at once (SMILES, Simplified Graph, Graph)
python run.py --data smiles simple_graph carbon --model GPT4o_20241120

# Increase parallel API calls for faster inference
python run.py --data smiles --model GPT4o_20241120 --api-nproc 32

# Resume an interrupted run (skip already completed samples)
python run.py --data smiles --model GPT4o_20241120 --reuse
```

**Key arguments:**

| Argument | Description |
| :--- | :--- |
| `--data` | Recognition task to run: SMILES, Simplified Graph, or Graph |
| `--model` | Model name as defined in `vlmeval/config.py` |
| `--work-dir` | Output directory (default: `./outputs`) |
| `--api-nproc` | Number of parallel API calls (default: 4, increase for faster inference) |
| `--reuse` | Reuse existing prediction files to resume interrupted runs |

Prediction results will be saved to `VLMEvalKit/outputs/<model_name>/`.

**Testing with your own model:**

To evaluate a custom model, you need to implement a model wrapper in VLMEvalKit. At minimum, create a class with a `generate_inner(msgs, dataset=None)` method that takes a multi-modal message list and returns the model's prediction string. Then register it in `vlmeval/config.py`. For details, see the [VLMEvalKit Development Guide](https://github.com/open-compass/VLMEvalKit/blob/main/docs/en/Development.md#implement-a-new-model).

### Step 5: Convert Results

VLMEvalKit outputs an XLSX file per run. Convert it to the JSONL format expected by the Evaluator:

```bash
# Convert XLSX → Evaluator JSONL
python convert_result.py \
    -i "VLMEvalKit/outputs/GPT4o_20241120/T20260413_G/GPT4o_20241120_chem_smiles.xlsx" \
    -o "results/GPT4o_20241120_chem_smiles.jsonl"
```

### Step 6: Evaluation

After inference, use the Evaluator to compute accuracy on three tracks. The Evaluator takes two JSONL files — ground truth and predictions.

**Evaluation metrics:**

| Metric | What it compares | Description |
| :--- | :--- | :--- |
| **SMILES Accuracy** | SMILES strings | Converts both GT and prediction to SMILES, then compares canonical SMILES string. |
| **Simplified Graph Accuracy** | Atom symbols + bond types | Graph isomorphism on simplified molecular graph (ignoring charges, radicals, valences, isotopes, attachment point, brackets). |
| **Graph Accuracy** | CARBON | Graph isomorphism on the complete molecular graph including all attributes. |

**Running evaluation:**

```bash
python evaluate/eval_SMILES.py --gt_path dataset/annotation.jsonl --pred_path results/GPT4o_20241120_chem_smiles.jsonl
# Output:
# SMILES Precision: 0.0797

python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/GPT4o_20241120_chem_graph_simple.jsonl
# Output:
# Simplified Graph Precision: 0.0374

python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/GPT4o_20241120_chem.jsonl
# Output:
# SMILES Precision          : 0.0
# Simplified Graph Precision: 0.0344
# Graph Precision           : 0.0298
```

## Benchmark Results

We evaluated 18 mainstream models(The inference results are saved in the `results` folder), revealing that existing methods suffer significant performance drops in real-world scenarios.
_Underlined values indicate the best results within each class, and bold values represent the overall best results across all classes._

| Method | SMILES | Simplified Graph | Graph |
|--------|--------|------------------|-------|
| **SMILES-based Expert Models** |||| 
| OCSU |6.06 | - | - |
| DECIMERv2.2 | 22.84 | - | - |
| **Graph-based Expert Models** |||| 
| MolGrapher | 20.33 | 22.81 | - |
| MolNexTR | 40.9 | 34.42 | - |
| MolScribe | 41.05 | 34.74 | - |
| GTR-Mol-VLM | 40.43 | 35.22 | - |
| **Vision Language Models** |||| 
| GPT-4o | 7.94 | 3.74 | 2.94 |
| Qwen-VL-Max |6.95 | 5.83 | 3.66 |
| InternVL3.5 | 25.6 | 6.88 | 3.08 |
| ChemVLM† | 4.79 | - | - |
| ChemDFM-X† | 9.75 | - | - |
| **Vision Reasoning Models** |||| 
| GPT-5 | 19.68 | 10.0 | 8.19 |
| Seed1.6-Thinking | 15.6 | 7.14 | 4.61 |
| Intern-S1 | 18.98 | 6.62 | 3.46 |
| Gemini 2.5 Pro | 30.06 | 15.67 | 13.04 |
| GLM-4.5V | 12.13 |7.89 | 4.26 |
| **Tools** |||| 
| Mathpix | 27.88 | - | - |
| Logics-Parsing | 15.47 | - | - |

Please refer to the paper for complete results.


<!-- ## Citation

If you use MolRecBench-Wild, the MOSAIC framework, or the CARBON notation in your research, please cite our paper:

```bibtex
@inproceedings{anonymous2026molrecbench,
  title={MolRecBench-Wild: A Real-World Benchmark for Optical Chemical Structure Recognition},
  author={Anonymous CVPR Submission},
  booktitle={Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)},
  year={2026}
}
``` -->
