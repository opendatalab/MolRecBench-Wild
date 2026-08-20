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
  <a href="README.md">🇬🇧 English</a>
</p>

<p align="center">
  <img src="assets/why_molrecbench_wild.png" width="50%" alt="Why Molrecbench Wild" />
</p>

## 🔥 News

- 🚀 [2026-05-07] MolRecBench-Wild v1 已在 [arXiv](https://arxiv.org/abs/2605.05832) 发布。

## 📊 数据集统计

| 项目 | 当前仓库发布版 |
| :--- | :--- |
| **发布标识** | `2026-08-19` |
| **数据来源** | 学术论文中的分子结构图 |
| **样本数** | 5,024 |
| **标注真值** | CARBON 分子图标注 |
| **难度元数据** | `hardcase_label`（`2026-08-19` 版本中共有 50 种不同取值） |
| **评测子集** | A：1,987；B：1,976；C：1,061 |
| **评测任务** | SMILES、简化图和完整图 |

arXiv v1 论文介绍的是较早的 5,029 样本快照。当前仓库以
5,024 样本的 `2026-08-19` 为权威真值版本。

## 项目结构

```text
.
├── assets/                  README 图片
├── evaluate/                评测包（`python -m evaluate`）
├── patches/                 固定版本的 VLMEvalKit 集成补丁
├── prompts/                 各任务提示词与视觉示例
├── results/                 仓库自带的预测 JSONL 文件
│   └── manifest.json         预测结果完整性元数据
└── scripts/                 安装、转换、校验与发布工具
```

`dataset/`、`LMUData/` 和 `VLMEvalKit/` 会在运行时生成，不纳入版本控制。

## CARBON 数据格式

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

## ⚡ 快速开始

### 第一步：环境安装

```bash
git clone https://github.com/opendatalab/MolRecBench-Wild.git
cd MolRecBench-Wild

# 创建并激活虚拟环境，然后安装依赖
conda create -n molrec python=3.10 -y
conda activate molrec
python -m pip install -r requirements.txt
```

### 第二步: 配置 VLMEvalKit

我们使用 [VLMEvalKit](https://github.com/open-compass/VLMEvalKit) 进行模型推理。
安装脚本会检出固定的上游 commit
`b9ff66c970449a8106c02570102bcfb2fb3df462`，并应用
[`patches/`](patches/) 中的化学任务集成补丁。VLMEvalKit 本身从上游获取，
不在本仓库中重新分发。

运行一键安装脚本:

```bash
bash scripts/setup_vlmevalkit.sh
```

使用 API 模型时，请将所选适配器需要的凭据写入
`VLMEvalKit/.env`。本地模型适配器不需要下面的 OpenAI 变量。
不要将该文件提交到 Git。

```bash
# VLMEvalKit/.env
OPENAI_API_BASE=https://your-api-base-url
OPENAI_API_KEY=your-api-key
```

### 第三步: 下载并转换数据集

从 HuggingFace 下载数据集，并一步将其转换为 VLMEvalKit 的 TSV 格式：

```bash
# 下载数据集，并生成三个任务所需的全部 TSV 文件
python scripts/download_and_convert_dataset.py --prompt all

# 下载数据集，并转换成 SMILES 任务的 TSV 文件
python scripts/download_and_convert_dataset.py --prompt smiles

# 如果数据集已经下载，可以通过 skip-download 参数来仅转换格式
python scripts/download_and_convert_dataset.py --prompt smiles --skip-download
```

这个脚本会进行如下操作:

1. 下载数据集到 `./dataset/images/` 并且保存标注信息到 `./dataset/annotation.jsonl`
2. 生成 TSV 文件保存到 `./LMUData/`
3. 自动在 `VLMEvalKit/.env` 中注册 `LMUData` 路径，以便 VLMEvalKit 能够找到这些 TSV 文件。

下载器固定使用 Hugging Face 上不可变的 `2026-08-19` 发布 revision
`e8999662272ee5a9fd565e5dabf28feb12962dee`。转换前会检查 5,024 个 ID、
必需标注字段、评测子集数量、原子字段长度和本地图片完整性。

### 第四步: 运行推理脚本

```bash
cd VLMEvalKit

# 一次推理一个任务 (SMILES)
python run.py --data chem_smiles --model GPT4o_20241120

# 一次推理三个任务 (SMILES, Simplified Graph, Graph)
python run.py --data chem_smiles chem_graph_simple chem_graph --model GPT4o_20241120

# 使用并行API调用来提高推理速度
python run.py --data chem_smiles --model GPT4o_20241120 --api-nproc 32

# 恢复一个中断的运行（跳过已完成的样本）
python run.py --data chem_smiles --model GPT4o_20241120 --reuse
```

**关键参数:**

| 参数            | 描述                                                              |
| :-------------- | :---------------------------------------------------------------- |
| `--data`      | 要运行的数据集 ID：`chem_smiles`、`chem_graph_simple` 或 `chem_graph` |
| `--model`     | `vlmeval/config.py`中定义的模型名称                             |
| `--work-dir`  | 输出文件夹 (default:`./outputs`)                                |
| `--api-nproc` | 并行 API 调用的数量（默认值为 4，可增大以加快推理速度）           |
| `--reuse`     | 复用已有的预测文件以恢复中断的运行                                |

预测结果将保存在 `VLMEvalKit/outputs/<model_name>/`。

**测试你自己的模型:**

要评估自定义模型，需要在 VLMEvalKit 中实现模型封装（wrapper）。
至少创建一个包含 `generate_inner(msgs, dataset=None)` 方法的类，
用于接收多模态消息列表并返回预测字符串，然后将其注册到
`vlmeval/config.py`。详见[固定上游 commit 对应的开发指南](https://github.com/open-compass/VLMEvalKit/blob/b9ff66c970449a8106c02570102bcfb2fb3df462/docs/en/Development.md#implement-a-new-model)。

### 第五步：准备预测 JSONL

推理完成后，先返回仓库根目录：

```bash
cd ..
```

评测器读取每行一个 JSON 对象的文件。每条预测必须使用与
`dataset/annotation.jsonl` 完全一致的 `id`。SMILES 预测至少需要
`id` 和 `smiles`；图预测使用上文展示的 CARBON 字段。

转换 VLMEvalKit 工作簿时需要显式指定任务：

```bash
python scripts/convert_result.py \
  --input "VLMEvalKit/outputs/<model>/<run-id>/<prediction>.xlsx" \
  --output "local_results/<model>_graph.jsonl" \
  --track graph \
  --strict-predictions \
  --errors-output "/tmp/<model>_graph_errors.jsonl"
```

数据集与转换任务的映射是 `chem_smiles` → `smiles`、
`chem_graph_simple` → `s_graph`、`chem_graph` → `graph`。文本文件名 ID
（包括当前的 `.jpg` ID）默认保持其值；首尾空白会被去除，数值单元格会
被规范化。只有旧工作簿的 ID 确实缺少后缀时才使用 `--id-suffix .jpg`。
多 sheet 工作簿必须通过 `--sheet NAME` 选择一页，或显式使用
`--all-sheets` 合并；合并的所有 sheet 之间也不能有重复 ID。对于历史
CARBON attachment-point 预测，`atom1` 表示保留的真实原子，`atom2` 表示
转换时删除的 dummy 原子。解析失败的预测仍以空预测保留其 ID；启用
`--strict-predictions` 后，只要存在此类错误就不会替换原输出文件。

如需强制检查某个自定义 JSONL 目录是否精确覆盖 5,024 个 ID，运行：

```bash
python scripts/validate_results.py \
  --results local_results \
  --write-manifest /tmp/local_results_manifest.json
```

### 第六步: 评估

推理完成后，使用 Evaluator 在三个任务上计算准确率。
Evaluator 接收两个 JSONL 文件——标注信息（ground truth）和预测结果（predictions）。

**评测指标：**

| 指标 | 比较内容 | 说明 |
| :--- | :--- | :--- |
| **SMILES 准确率** | 规范 SMILES | 仅评测可从 CARBON 转换、展开缩写并成功规范化的 GT。精确比较规范 SMILES；默认忽略双键 cis/trans，但保留原子手性比较。 |
| **简化图准确率** | 原子符号与简化键类型 | 对符号和键类型简化后的有向图进行同构判断；忽略化学原子属性、连接点、括号和坐标。 |
| **图准确率** | CARBON 化学属性 | 对原子符号、电荷、自由基、价态、同位素、连接点、键，以及括号别名/原子成员关系进行有向图同构判断。不比较坐标和括号显示矩形。 |

**运行评估命令:**

```bash
python -m evaluate smiles \
  --gt-path dataset/annotation.jsonl \
  --pred-path results/MLLM/GPT-5.6-sol/GPT-5.6-sol_smiles.jsonl
# 当前结果：1,791 / 2,392 条可评测 GT = 0.7487458194

python -m evaluate s_graph \
  --gt-path dataset/annotation.jsonl \
  --pred-path results/MLLM/GPT-5.6-sol/GPT-5.6-sol_graph_simple.jsonl
# 当前结果：1,828 / 5,024 GT = 0.3638535032

python -m evaluate graph \
  --gt-path dataset/annotation.jsonl \
  --pred-path results/MLLM/GPT-5.6-sol/GPT-5.6-sol_graph.jsonl
# 当前结果：1,636 / 5,024 GT = 0.3256369427
```

SMILES 评测默认忽略双键 cis/trans 斜线方向，与基准评测口径一致；原子手性
（`@`/`@@`）始终参与比较。如需同时比较两类立体化学信息，可添加
`--preserve-cistrans`。

评测默认要求预测 ID 完整且唯一。缺失 ID、GT 之外的额外 ID、重复 ID、
格式错误行或不含字符串 ID 的行都会终止评测。使用 `--limit` 或 `--split`
时，可以保留未被选中的 GT 预测，但所有被选中的 GT ID 都必须存在。只有
在明确进行不完整 ID 覆盖诊断时才应使用 `--allow-coverage-mismatch`；
Graph 任务中的非法 JSON 仍会直接报错。

如需确认仓库结果文件完整覆盖 5,024 个 GT ID，运行：

```bash
python scripts/validate_results.py
```

如需递归评估 `results/` 下所有可识别的 JSONL，并写入论文样式的
Excel 汇总表，运行：

```bash
python -m evaluate.eval_all --timeout 0
# 默认输出：results/evaluation_results.xlsx
```

下文表格使用 `--timeout 0`，即禁用单条图同构超时。这会增加耗时，
但可避免平台差异导致的小幅超时波动；默认超时为 5 秒。可使用
`--output`、`--include` 或 `--exclude` 自定义输出和筛选结果；
`--limit` 和 `--max-files` 可用于冒烟测试。
批量评测采用相同的严格 ID 覆盖规则；只有明确预期不完整结果时才传入
`--allow-coverage-mismatch`。

`dataset/annotation.jsonl` 中的每条记录都包含 `evaluation_subset` 字段。
论文表格中的映射为：

- A：不包含指定的化学语义属性难例标签，且视觉难例标签相对较少（1,987 条）
- B：不包含指定的化学语义属性难例标签，但视觉难例标签更多（1,976 条）
- C：包含指定的化学语义属性难例标签（1,061 条）

数据中的 `evaluation_subset` 直接存储字符串 `A`、`B`、`C`，定义遵循
[MinerU.Chem](https://arxiv.org/abs/2608.03525)。

## 基准测试结果

仓库当前包含 34 个预测 JSONL，覆盖 17 个系统。下表是使用当前评测器、
`2026-08-19` 版本和 `--timeout 0` 重新计算的精确匹配准确率（%）。
SMILES 的 Full、A、B、C 分母分别为 2,392、1,219、875 和 298；
Graph 的对应分母分别为 5,024、1,987、1,976 和 1,061。
破折号表示仓库未包含对应预测文件。
这些数值不能与 arXiv v1 的 5,029 样本结果直接比较。

| 方法 | Full SMILES | Full Graph | A SMILES | A Graph | B SMILES | B Graph | C SMILES | C Graph |
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

## 引用

如果在研究中使用 MolRecBench-Wild、MOSAIC 或 CARBON，请引用我们的 [CVPR 2026 论文](https://openaccess.thecvf.com/content/CVPR2026F/html/Yang_MolRecBench-Wild_A_Real-World_Benchmark_for_Optical_Chemical_Structure_Recognition_CVPRF_2026_paper.html)（同时提供 [arXiv 版本](https://arxiv.org/abs/2605.05832)）。配套的 [MinerU.Chem 技术报告](https://arxiv.org/abs/2608.03525)介绍了更新后的数据集发布版本和系统结果：

```bibtex
@inproceedings{yang2026molrecbench,
  title={MolRecBench-Wild: A Real-World Benchmark for Optical Chemical Structure Recognition},
  author={Yang, Haote and Wang, Hui and Zhu, Chen and Wang, Jingchao and Li, Linye and Lai, Hongbin and Ao, Huijie and Lyu, Yongxuan and Wu, Jiang and Sun, Jiaxing and Chen, Lua and Cao, Yuanyuan and Zhang, Ruijie and Lu, Shengxin and Wu, Lijun and Wang, Bin and He, Conghui},
  booktitle={Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition},
  year={2026}
}
```

## 许可证

项目原创源代码使用 Apache License 2.0，详见 [`LICENSE`](LICENSE)。
该许可证不会自动覆盖数据集图像或标注、模型权重、
预测输出、第三方软件或第三方资产。使用或再分发前，请阅读
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) 及适用的上游条款。
