# U-MolRecBench-Wild: A Real-World Benchmark for Optical Chemical Structure Recognition

[![Dataset](https://img.shields.io/badge/Dataset-HuggingFace-orange?logo=huggingface)](https://huggingface.co/datasets/opendatalab/U-MolRecBench-Wild)
<!-- [![Paper](https://img.shields.io/badge/Paper-CVPR%202026-red.svg)](https://arxiv.org/abs/xxxx.xxxxx)  -->
**U-MolRecBench-Wild** is a benchmark suite for Optical Chemical Structure Recognition (OCSR) derived from real-world chemical literature. Unlike existing benchmarks primarily based on patents or synthetic images, this dataset captures the visual noise and complex chemical semantic challenges found in authentic academic scenarios.

This repository includes:
- 📊 **U-MolRecBench-Wild Dataset**: 5029 molecular structure graphs from 820 recent chemical papers.
- 🧩 **MOSAIC Framework**: The first dual-dimension (Visual Presentation + Chemical Semantics) difficulty assessment system with 42 fine-grained labels.
- 🧪 **CARBON Notation**: A novel molecular representation language capable of expressing valence changes, icon-based groups, and other non-standard chemical semantics.
- 📏 **Evaluation Toolkit**: A dual-track evaluation protocol supporting both CARBON and SMILES outputs.

## 📖 Table of Contents

- [Introduction](#introduction)
- [Key Features](#key-features)
- [Dataset Statistics](#dataset-statistics)
- [Installation](#installation)
- [Usage](#usage)
- [CARBON Notation](#carbon-notation)
- [Benchmark Results](#benchmark-results)
- [Citation](#citation)
- [License](#license)

## Introduction

Optical Chemical Structure Recognition (OCSR) aims to convert molecular diagrams in scientific literature into machine-readable formats. However, due to significant visual complexity and chemical diversity in real images, existing systems perform poorly in authentic scenarios.

We introduce **MOSAIC** (Molecular Optical-Semantic Assessment of Image Complexity), a dual-dimension difficulty framework to quantify visual noise and chemical semantic challenges. Based on this, we constructed **MolRecBench-Wild**, a benchmark set of 5029 structures covering the full spectrum of difficulties observed in real publications.

To address the limitations of SMILES and MolFile in expressing complex chemical information, we propose **CARBON** (Complex Atomic Representation and Bonding Object Notation), a representation language capable of precisely expressing non-standard bonds, mixed valences, and icon-based groups.

## Key Features

*   **Real-World Source**: Data sourced entirely from 820 recent high-impact chemical journal articles (CC-BY-4.0 licensed), not patents or synthetic data.
*   **High Complexity**: 93.29% of samples have at least one MOSAIC difficulty label, and 42% are challenging in both visual and chemical dimensions.
*   **Rich Annotations**: Each sample is double-verified by domain experts and annotated with detailed MOSAIC difficulty labels.
*   **Multi-Format Support**: Ground Truth is provided in three formats: CARBON, Simplified Graph, and SMILES (where applicable).
*   **Dual-Track Evaluation**: Supports evaluation for models generating SMILES strings and models generating molecular graphs.

## Dataset Statistics

| Feature | MolRecBench-Wild | Traditional Benchmarks (e.g., USPTO, Staker) |
| :--- | :--- | :--- |
| **Source** | Academic Articles | Patents / Synthetic |
| **Sample Count** | 5029 | Varies (usually larger but simpler) |
| **Visual Difficulty Labels** | 18 Categories | < 10 Categories |
| **Chemical Difficulty Labels** | 24 Categories (MOSAIC subset) | < 3 Categories |
| **Ground Truth** | CARBON, Graph, SMILES | SMILES, MolFile |
| **Complex Structure Support** | Non-standard bonds, icon groups, mixed valences | Standard structures only |

## Installation

```bash
git clone https://github.com/your-username/MolRecBench-Wild.git
cd MolRecBench-Wild

# Install dependencies
conda create -n molrec python=3.10 -y
pip install -r requirements.txt
```

## Usage
```bash
sh eval.sh
```

## CARBON Notation

CARBON (Complex Atomic Representation and Bonding Object Notation) is a core innovation of this project, designed to address the shortcomings of existing representation methods in expressing complex chemical semantics.
It supports:
Non-standard Bond Types: Dashed bonds, bold bonds, mixed bond orders, etc.
Rich Atomic Properties: Oxidation states, radicals, isotopes, non-integer charges.
Repeating Structures: Explicit representation of polymers and repeating units.
Spatial Coordinates: Retains image-level 2D coordinate information.
Example (JSON Format):

```json
{
  "atoms": [
    {"id": 0, "atom": "O", "point_2d": [9.0, -8.0]},
    {"id": 1, "atom": "S", "point_2d": [9.0, -9.1]},
    {"id": 2, "atom": "CF3", "point_2d": [9.5, -9.9]}, 
    {"id": 4, "atom": "Rα", "point_2d": [8.0, -9.1]} 
  ],
  "bonds": [
    {"atom1": 0, "atom2": 1, "bond_type": "double"},
    {"atom1": 1, "atom2": 4, "bond_type": "any"} 
  ]
}
```


## Benchmark Results

We evaluated 18 mainstream models, revealing that existing methods suffer significant performance drops in real-world scenarios.

| Model Category | Model Name | SMILES Acc (%) | Simplified Graph Acc (%) | Graph Acc (%) |
| :--- | :--- | :--- | :--- | :--- |
| Expert (Graph) | GTR-Mol-VLM | 33.32 | 32.66 | - |
| Expert (Graph) | MolScribe | 28.11 | 32.35 | - |
| VLM | Gemini 2.5 Pro | 27.50 | 15.58 | 12.50 |
| VLM | InternVL3.5 | 24.39 | 6.83 | 3.73 |
| Expert (SMILES) | DECIMER v2.2 | 20.27 | - | - |
| Tool | Mathpix | 27.32 | - | - |

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

<!-- ## Acknowledgements
We thank all domain experts who participated in data annotation and verification. -->
