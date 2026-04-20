#!/usr/bin/env python3
"""
批量将 CSV 文件转换为评估脚本需要的 JSONL 格式

输入目录: transferd_csv_results_0127
输出目录: eval_data_0127

CSV 格式: {model_name}_chem_uspto.csv
  - 列: img_id, symbols, charges, isotopes, valences, radicals, coords, edges, brackets, smiles
"""

import ast
import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# ==================== 配置区域 ====================
SCRIPT_DIR = Path(__file__).parent.parent.parent  # VLMEvalKit 目录
CSV_INPUT_DIR = SCRIPT_DIR / "transferd_csv_results_0127"
JSONL_OUTPUT_DIR = SCRIPT_DIR / "eval_data_0127"

# 数据集名称
DATASET_NAME = "chem_uspto"

# 需要处理的模型列表
MODELS_TO_PROCESS = [
    "Doubao-Seed-1-6-Vision-250815",
    "Gemini2.5-Pro-OpenAI",
    "GLM-4.5v",
    "gpt-5-2025-08-07",
    "GPT4o_20241120",
    "QwenVLMax-OpenAI",
    "InternVL3.5-241B-A28B-API",
    "Intern-S1-API",
]

# 图片路径模板（根据 img_id 构造）
IMAGE_PATH_TEMPLATE = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/USPTO/{img_id}.png"

# ==================== 配置区域结束 ====================


def parse_list_string(s: str) -> List:
    """解析字符串形式的列表"""
    if not s or s.strip() == '[]' or s.strip() == '':
        return []
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return []


def format_atoms(symbols: List[str], coords: List[List[int]]) -> List[Dict]:
    """将 symbols 和 coords 转换为 atoms 格式"""
    atoms = []
    for idx, (symbol, coord) in enumerate(zip(symbols, coords)):
        atoms.append({
            "a": symbol,
            "id": idx,
            "xy": coord
        })
    return atoms


def format_bonds(edges: List[List[int]], atoms: List[Dict]) -> List[Dict]:
    """将 edges 转换为 bonds 格式"""
    num_atoms = len(atoms)
    if num_atoms == 0:
        return atoms
    
    graph = [[0] * num_atoms for _ in range(num_atoms)]
    
    for edge in edges:
        if len(edge) >= 3:
            atom1, atom2, b_type = edge[0], edge[1], edge[2]
            if b_type == 5:
                forward_b_type = 5
                backward_b_type = 6
            elif b_type == 6:
                forward_b_type = 6
                backward_b_type = 5
            else:
                forward_b_type = b_type
                backward_b_type = b_type
            
            if atom1 < num_atoms and atom2 < num_atoms:
                graph[atom1][atom2] = forward_b_type
                graph[atom2][atom1] = backward_b_type
    
    atoms_bonds = []
    for idx, atom in enumerate(atoms):
        atoms_bonds.append(atom)
        for jdx in reversed(range(idx)):
            if graph[jdx][idx] != 0:
                atoms_bonds.append({
                    "b": graph[jdx][idx],
                    "a1": jdx,
                    "a2": idx,
                })
    
    return atoms_bonds


def create_user_prompt() -> str:
    """创建 user 角色的 prompt"""
    return """\n<image>
You are viewing a diagram of a chemical molecular structure.
First, list all the atom types and their coordinates from the image, followed by detailing all the chemical bonds.
The types of chemical bonds include ['single', 'double', 'triple', 'aromatic', 'solid wedge', 'dashed wedge'].
For wedge bonds, the direction is drawn from atom1 to atom2:
a solid wedge indicates that atom2 is protruding out of the plane towards the observer;
while a dashed wedge indicates that atom2 is receding into the plane away from the observer.
Present the results in JSON list format without any additional text.
Example format:
```json
{
    "atoms": [
        {
            "a": "C", 
            "id": 0, 
            "xy": [x1, y1]
        },
        ...
    ],
    "bonds": [
        {
            "b": 1,
            "a1": 0,
            "a2": 1,
        },
        ...
    ]
}
```
Strictly follow the given format and do not add any extra explanations or content."
Finally, based on the atoms and bonds that you have listed, you should output a canonical SMILES string of the molecule in JSON format with the key 'smiles'.
Example format:
```json
{
    "smiles": "C1=CC=CC=C1"
}
```
Again, strictly follow the given format and do not add any extra explanations or content.\""""


def create_response_content(atoms_bonds: List[Dict], smiles: str) -> str:
    """创建 assistant 角色的 response 内容"""
    atoms_bonds_json = json.dumps(atoms_bonds, separators=(',', ':'))
    response = f"\n```json\n{atoms_bonds_json}\n```\n```json\n{{\n    \"smiles\": \"{smiles}\"\n}}\n```\n"
    return response


def find_model_csv_file(model_name: str, root_dir: Path) -> Optional[Path]:
    """递归查找指定模型的 CSV 文件"""
    file_pattern = f"{model_name}_{DATASET_NAME}.csv"
    
    found_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file == file_pattern:
                found_files.append(Path(root) / file)
    
    if found_files:
        found_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return found_files[0]
    
    return None


def convert_csv_to_jsonl(csv_path: Path, output_jsonl: Path) -> Dict:
    """将单个 CSV 文件转换为 JSONL 格式"""
    records_written = 0
    records_skipped = 0
    
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    
    with open(csv_path, 'r', encoding='utf-8') as csv_file, \
         open(output_jsonl, 'w', encoding='utf-8') as jsonl_file:
        
        reader = csv.DictReader(csv_file)
        
        for row_num, row in enumerate(reader, start=2):
            img_id = row.get('img_id', '').strip()
            
            if not img_id:
                records_skipped += 1
                continue
            
            # 解析字段
            symbols = parse_list_string(row.get('symbols', ''))
            coords = parse_list_string(row.get('coords', ''))
            edges = parse_list_string(row.get('edges', ''))
            smiles = row.get('smiles', '').strip()
            
            # 构造图片路径
            image_path = IMAGE_PATH_TEMPLATE.format(img_id=img_id)
            
            try:
                # 如果有 symbols 和 coords，格式化 atoms 和 bonds
                if symbols and coords and len(symbols) == len(coords):
                    atoms = format_atoms(symbols, coords)
                    if edges:
                        atoms_bonds = format_bonds(edges, atoms)
                    else:
                        atoms_bonds = atoms
                else:
                    # 如果没有 atoms/bonds 信息，只保留 smiles
                    atoms_bonds = []
                
                # 创建 response 内容
                response_content = create_response_content(atoms_bonds, smiles)
                
                # 构造 JSONL 记录
                record = {
                    "response": response_content,
                    "labels": None,
                    "logprobs": None,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant.",
                            "loss": None
                        },
                        {
                            "role": "user",
                            "content": create_user_prompt(),
                            "loss": None
                        },
                        {
                            "role": "assistant",
                            "content": response_content
                        }
                    ],
                    "images": [
                        {
                            "bytes": None,
                            "path": image_path
                        }
                    ]
                }
                
                jsonl_file.write(json.dumps(record, ensure_ascii=False) + '\n')
                records_written += 1
                
            except Exception as e:
                print(f"  Error processing row {row_num} (img_id: {img_id}): {e}", file=sys.stderr)
                records_skipped += 1
                continue
    
    return {
        'records_written': records_written,
        'records_skipped': records_skipped
    }


def process_model(model_name: str) -> Dict:
    """处理单个模型"""
    print(f"\n{'='*60}")
    print(f"处理模型: {model_name}")
    print(f"{'='*60}")
    
    result = {
        'model': model_name,
        'found': False,
        'converted': False,
        'records_written': 0,
        'records_skipped': 0,
        'error': None
    }
    
    # 查找 CSV 文件
    csv_file = find_model_csv_file(model_name, CSV_INPUT_DIR)
    
    if not csv_file:
        print(f"  ⚠️  未找到 CSV 文件: {model_name}_{DATASET_NAME}.csv")
        return result
    
    result['found'] = True
    print(f"  ✅ 找到 CSV 文件: {csv_file}")
    
    # 构造输出路径
    output_jsonl = JSONL_OUTPUT_DIR / f"{model_name}.jsonl"
    
    try:
        # 转换
        convert_result = convert_csv_to_jsonl(csv_file, output_jsonl)
        result['records_written'] = convert_result['records_written']
        result['records_skipped'] = convert_result['records_skipped']
        result['converted'] = True
        print(f"  ✅ 转换成功: {output_jsonl}")
        print(f"     - 写入记录: {result['records_written']}")
        if result['records_skipped'] > 0:
            print(f"     - 跳过记录: {result['records_skipped']}")
    except Exception as e:
        result['error'] = str(e)
        print(f"  ❌ 转换失败: {e}")
    
    return result


def main():
    print("=" * 60)
    print("批量转换 CSV 文件为 JSONL 格式")
    print("=" * 60)
    print(f"输入目录: {CSV_INPUT_DIR}")
    print(f"输出目录: {JSONL_OUTPUT_DIR}")
    print(f"数据集: {DATASET_NAME}")
    print(f"需要处理的模型数量: {len(MODELS_TO_PROCESS)}")
    print()
    
    # 检查输入目录
    if not CSV_INPUT_DIR.exists():
        print(f"❌ 错误: 输入目录不存在: {CSV_INPUT_DIR}")
        sys.exit(1)
    
    # 创建输出目录
    JSONL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ 输出目录: {JSONL_OUTPUT_DIR}")
    
    # 处理每个模型
    all_results = []
    total_success = 0
    total_fail = 0
    total_missing = 0
    total_records = 0
    
    for i, model_name in enumerate(MODELS_TO_PROCESS, 1):
        print(f"\n[{i}/{len(MODELS_TO_PROCESS)}] 处理模型: {model_name}")
        result = process_model(model_name)
        all_results.append(result)
        
        if result['found']:
            if result['converted']:
                total_success += 1
                total_records += result['records_written']
            else:
                total_fail += 1
        else:
            total_missing += 1
    
    # 输出总结
    print("\n" + "=" * 60)
    print("转换完成总结")
    print("=" * 60)
    print(f"\n处理模型数量: {len(MODELS_TO_PROCESS)}")
    print(f"\n转换结果:")
    print(f"  ✅ 成功转换: {total_success}")
    print(f"  ❌ 转换失败: {total_fail}")
    print(f"  ⚠️  文件缺失: {total_missing}")
    print(f"\n总记录数: {total_records}")
    
    # 详细错误信息
    has_errors = any(result['error'] for result in all_results)
    if has_errors:
        print("\n详细错误信息:")
        for result in all_results:
            if result['error']:
                print(f"  {result['model']}: {result['error']}")
    
    # 缺失文件
    missing_models = [result['model'] for result in all_results if not result['found']]
    if missing_models:
        print("\n缺失文件的模型:")
        for model in missing_models:
            print(f"  ⚠️  {model}")
    
    print("\n" + "=" * 60)
    print(f"JSONL 文件保存在: {JSONL_OUTPUT_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    main()
