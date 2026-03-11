#!/usr/bin/env python3
"""
将推理结果的CSV文件转换为评估脚本需要的JSONL格式

输入：
- graph_csv: 包含atoms和bonds信息的CSV文件
- smiles_csv: 包含smiles信息的CSV文件
- jsonl_with_paths: 包含图片路径的JSONL文件（用于获取图片路径）

输出：
- output_jsonl: 评估脚本需要的JSONL格式
"""

import argparse
import ast
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# ==================== 配置区域 ====================
# 默认配置（可以根据需要修改）
# 注意：相对路径相对于脚本所在目录的父目录（VLMEvalKit目录）
# DEFAULT_GRAPH_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/GPT4o_20241120/T20260106_G6ae70ffa/GPT4o_20241120_abbr_graph.csv"
# DEFAULT_SMILES_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/GPT4o_20241120/T20260106_G6ae70ffa/GPT4o_20241120_abbr_smiles.csv"
# DEFAULT_GRAPH_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/gpt-5-2025-08-07/T20260107_G6ae70ffa/gpt-5-2025-08-07_abbr_graph.csv"
# DEFAULT_SMILES_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/gpt-5-2025-08-07/T20260107_G6ae70ffa/gpt-5-2025-08-07_abbr_smiles.csv"

# DEFAULT_GRAPH_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/gpt-5-2025-08-07/T20260106_G6ae70ffa/gpt-5-2025-08-07_abbr_graph.csv"
# DEFAULT_SMILES_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/gpt-5-2025-08-07/T20260106_G6ae70ffa/gpt-5-2025-08-07_abbr_smiles.csv"

# DEFAULT_GRAPH_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/Doubao-Seed-1-6-Vision-250815/T20260107_G6ae70ffa/Doubao-Seed-1-6-Vision-250815_abbr_graph.csv"
# DEFAULT_SMILES_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/Doubao-Seed-1-6-Vision-250815/T20260107_G6ae70ffa/Doubao-Seed-1-6-Vision-250815_abbr_smiles.csv"

# DEFAULT_GRAPH_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/interns1_graph.csv"
# DEFAULT_SMILES_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/inters1_smiles.csv"

# DEFAULT_GRAPH_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/QwenVLMax-250408-OpenAI/T20260107_G6ae70ffa/QwenVLMax-250408-OpenAI_abbr_graph_0107.csv"
# DEFAULT_SMILES_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/QwenVLMax-250408-OpenAI/T20260107_G6ae70ffa/QwenVLMax-250408-OpenAI_abbr_smiles_0107.csv" 

# DEFAULT_GRAPH_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/Gemini2.5-Flash-OpenAI/T20260107_G6ae70ffa/Gemini2.5-Flash-OpenAI_abbr_graph_0107.csv"
# DEFAULT_SMILES_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/Gemini2.5-Flash-OpenAI/T20260107_G6ae70ffa/Gemini2.5-Flash-OpenAI_abbr_smiles_0107.csv"

# DEFAULT_GRAPH_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/QwenVLMax-OpenAI/QwenVLMax-OpenAI_abbr_graph_0107.csv
# DEFAULT_SMILES_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/QwenVLMax-OpenAI/QwenVLMax-OpenAI_abbr_smiles_0107.csv"
DEFAULT_GRAPH_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/QwenVLMax-OpenAI/T20260108_G6ae70ffa/QwenVLMax-OpenAI_abbr_graph_0107.csv"
DEFAULT_SMILES_CSV = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/transferd_csv_results/QwenVLMax-OpenAI/T20260108_G6ae70ffa/QwenVLMax-OpenAI_abbr_smiles_0107.csv"

DEFAULT_OUTPUT_JSONL = "eval_data/QwenVLMax-OpenAI.jsonl"  
DEFAULT_JSONL_WITH_PATHS = "/mnt/dhwfile/MinerU4S/aohuijie/VLMEvalKit/infer_data_abb2.jsonl"  # 可选，如果为None则根据img_id构造路径


# ==================== 配置区域结束 ====================

def parse_list_string(s: str) -> List:
    """解析字符串形式的列表，如 "['C', 'C', 'O']" 或 "[[0, 1], [2, 3]]" """
    if not s or s.strip() == '[]' or s.strip() == '':
        return []
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return []


def format_atoms(symbols: List[str], coords: List[List[int]]) -> List[Dict]:
    """
    将symbols和coords转换为atoms格式
    
    Args:
        symbols: 原子符号列表，如 ['C', 'C', 'O']
        coords: 坐标列表，如 [[0, 0], [1, 0], [2, 0]]
    
    Returns:
        atoms格式的列表，如 [{"a": "C", "id": 0, "xy": [0, 0]}, ...]
    """
    atoms = []
    for idx, (symbol, coord) in enumerate(zip(symbols, coords)):
        atoms.append({
            "a": symbol,
            "id": idx,
            "xy": coord
        })
    return atoms


def format_bonds(edges: List[List[int]], atoms: List[Dict]) -> List[Dict]:
    """
    将edges转换为bonds格式，并按照参考代码的逻辑排列
    
    Args:
        edges: 边列表，如 [[0, 1, 1], [1, 2, 2]]，格式为 [atom1, atom2, bond_type]
        atoms: atoms格式的列表
    
    Returns:
        atoms_bonds格式的列表（先atoms，然后bonds）
    """
    # 构建邻接矩阵
    num_atoms = len(atoms)
    graph = [[0] * num_atoms for _ in range(num_atoms)]
    
    for edge in edges:
        if len(edge) >= 3:
            atom1, atom2, b_type = edge[0], edge[1], edge[2]
            # 处理wedge bonds
            if b_type == 5:
                forward_b_type = 5
                backward_b_type = 6
            elif b_type == 6:
                forward_b_type = 6
                backward_b_type = 5
            else:
                forward_b_type = b_type
                backward_b_type = b_type
            
            graph[atom1][atom2] = forward_b_type
            graph[atom2][atom1] = backward_b_type
    
    # 按照参考代码的逻辑排列：先atoms，然后bonds
    atoms_bonds = []
    f_a_cnt = 0
    f_b_cnt = 0
    
    for idx, atom in enumerate(atoms):
        atoms_bonds.append(atom)
        f_a_cnt += 1
        # 检查与之前原子的连接
        for jdx in reversed(range(idx)):
            if graph[jdx][idx] != 0:
                atoms_bonds.append({
                    "b": graph[jdx][idx],
                    "a1": jdx,
                    "a2": idx,
                })
                f_b_cnt += 1
    
    # 验证
    assert f_a_cnt == len(atoms), f"Atom count mismatch: {f_a_cnt} != {len(atoms)}"
    assert f_b_cnt == len(edges), f"Bond count mismatch: {f_b_cnt} != {len(edges)}"
    
    return atoms_bonds


def load_image_paths(jsonl_path: Path) -> Dict[str, str]:
    """
    从JSONL文件加载图片路径映射
    
    Args:
        jsonl_path: JSONL文件路径
    
    Returns:
        {img_id: image_path} 的字典
    """
    image_paths = {}
    if jsonl_path.exists():
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line.strip())
                    img_id = data.get('data_id', '')
                    image_path = data.get('image_dir_p', '')
                    if img_id and image_path:
                        image_paths[img_id] = image_path
    return image_paths


def create_user_prompt() -> str:
    """创建user角色的prompt"""
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
    """
    创建assistant角色的response内容
    
    Args:
        atoms_bonds: atoms和bonds的混合列表
        smiles: SMILES字符串
    
    Returns:
        response字符串
    """
    # 将atoms_bonds转换为紧凑的JSON字符串（无空格）
    atoms_bonds_json = json.dumps(atoms_bonds, separators=(',', ':'))
    
    # 构造response格式
    response = f"\n```json\n{atoms_bonds_json}\n```\n```json\n{{\n    \"smiles\": \"{smiles}\"\n}}\n```\n"
    return response


def convert_csv_to_jsonl(
    graph_csv: Path,
    smiles_csv: Path,
    output_jsonl: Path,
    jsonl_with_paths: Optional[Path] = None
):
    """
    将CSV文件转换为JSONL格式
    
    Args:
        graph_csv: graph CSV文件路径
        smiles_csv: smiles CSV文件路径
        output_jsonl: 输出JSONL文件路径
        jsonl_with_paths: 包含图片路径的JSONL文件（可选）
    """
    # 加载图片路径映射
    image_paths = {}
    if jsonl_with_paths:
        image_paths = load_image_paths(jsonl_with_paths)
        print(f"加载了 {len(image_paths)} 个图片路径", file=sys.stderr)
    
    # 读取smiles CSV，建立img_id到smiles的映射
    smiles_map = {}
    with open(smiles_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_id = row.get('img_id', '').strip()
            smiles = row.get('smiles', '').strip()
            if img_id and smiles:
                smiles_map[img_id] = smiles
    
    print(f"加载了 {len(smiles_map)} 个SMILES记录", file=sys.stderr)
    
    # 处理graph CSV
    records_written = 0
    records_skipped = 0
    
    with open(graph_csv, 'r', encoding='utf-8') as graph_file, \
         open(output_jsonl, 'w', encoding='utf-8') as jsonl_file:
        
        reader = csv.DictReader(graph_file)
        
        for row_num, row in enumerate(reader, start=2):
            img_id = row.get('img_id', '').strip()
            
            if not img_id:
                print(f"Warning: Row {row_num} has empty img_id, skipping...", file=sys.stderr)
                records_skipped += 1
                continue
            
            # 解析CSV中的列表字段
            symbols = parse_list_string(row.get('symbols', ''))
            coords = parse_list_string(row.get('coords', ''))
            edges = parse_list_string(row.get('edges', ''))
            smiles = row.get('smiles', '').strip()
            
            # 如果graph CSV中没有smiles，从smiles CSV中获取
            if not smiles:
                smiles = smiles_map.get(img_id, '')
            
            # 检查必需字段
            if not symbols or not coords:
                print(f"Warning: Row {row_num} (img_id: {img_id}) has empty symbols or coords, skipping...", file=sys.stderr)
                records_skipped += 1
                continue
            
            if len(symbols) != len(coords):
                print(f"Warning: Row {row_num} (img_id: {img_id}) symbols and coords length mismatch, skipping...", file=sys.stderr)
                records_skipped += 1
                continue
            
            # 如果没有smiles，跳过（但可以继续处理graph部分）
            if not smiles:
                print(f"Warning: Row {row_num} (img_id: {img_id}) has no smiles, using empty string...", file=sys.stderr)
            
            try:
                # 格式化atoms
                atoms = format_atoms(symbols, coords)
                
                # 格式化bonds（如果edges不为空）
                if edges:
                    atoms_bonds = format_bonds(edges, atoms)
                else:
                    # 如果没有edges，只包含atoms
                    atoms_bonds = atoms
                
                # 创建response内容
                response_content = create_response_content(atoms_bonds, smiles)
                
                # 获取图片路径
                image_path = image_paths.get(img_id, '')
                if not image_path:
                    # 如果JSONL中没有，尝试从img_id构造路径
                    # 假设路径格式：/mnt/dhwfile/MinerU4S/jcwang/molecule_recognition/data/real_w_molfile/USPTO_30k_abbreviated/{img_id}.png
                    image_path = f"/mnt/dhwfile/MinerU4S/jcwang/molecule_recognition/data/real_w_molfile/USPTO_30k_abbreviated/{img_id}.png"
                
                # 构造JSONL记录
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
                
                # 写入JSONL
                jsonl_file.write(json.dumps(record, ensure_ascii=False) + '\n')
                records_written += 1
                
                # 每处理1000条记录输出一次进度
                if records_written % 1000 == 0:
                    print(f"Processed {records_written} records...", file=sys.stderr)
                    
            except Exception as e:
                print(f"Error processing row {row_num} (img_id: {img_id}): {e}", file=sys.stderr)
                records_skipped += 1
                continue
    
    print(f"\n✅ Successfully created {output_jsonl}", file=sys.stderr)
    print(f"   - Records written: {records_written}", file=sys.stderr)
    if records_skipped > 0:
        print(f"   - Records skipped: {records_skipped}", file=sys.stderr)


def main():
    # 获取脚本所在目录（VLMEvalKit目录）
    SCRIPT_DIR = Path(__file__).parent.parent.parent
    
    # 解析默认配置路径
    def resolve_path(path_str):
        """解析路径，如果是绝对路径则直接使用，否则相对于SCRIPT_DIR"""
        if not path_str:
            return None
        path = Path(path_str)
        if path.is_absolute():
            return path
        return SCRIPT_DIR / path_str
    
    # 使用默认配置
    graph_csv = resolve_path(DEFAULT_GRAPH_CSV)
    smiles_csv = resolve_path(DEFAULT_SMILES_CSV)
    output_jsonl = resolve_path(DEFAULT_OUTPUT_JSONL)
    jsonl_with_paths = resolve_path(DEFAULT_JSONL_WITH_PATHS) if DEFAULT_JSONL_WITH_PATHS else None
    
    # 支持命令行参数覆盖（可选）
    parser = argparse.ArgumentParser(
        description='将推理结果的CSV文件转换为评估脚本需要的JSONL格式'
    )
    parser.add_argument(
        '--graph-csv',
        default=None,
        help='Graph CSV文件路径（覆盖默认配置）'
    )
    parser.add_argument(
        '--smiles-csv',
        default=None,
        help='Smiles CSV文件路径（覆盖默认配置）'
    )
    parser.add_argument(
        '--output-jsonl',
        default=None,
        help='输出JSONL文件路径（覆盖默认配置）'
    )
    parser.add_argument(
        '--jsonl-with-paths',
        default=None,
        help='包含图片路径的JSONL文件（覆盖默认配置）'
    )
    
    args = parser.parse_args()
    
    # 如果提供了命令行参数，则覆盖默认配置
    if args.graph_csv:
        graph_csv = resolve_path(args.graph_csv)
    if args.smiles_csv:
        smiles_csv = resolve_path(args.smiles_csv)
    if args.output_jsonl:
        output_jsonl = resolve_path(args.output_jsonl)
    if args.jsonl_with_paths:
        jsonl_with_paths = resolve_path(args.jsonl_with_paths)
    
    # 检查输入文件是否存在
    if not graph_csv or not graph_csv.exists():
        print(f"Error: Graph CSV file '{graph_csv}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not smiles_csv or not smiles_csv.exists():
        print(f"Error: Smiles CSV file '{smiles_csv}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # 处理可选的JSONL文件
    if jsonl_with_paths and not jsonl_with_paths.exists():
        print(f"Warning: JSONL file with paths '{jsonl_with_paths}' does not exist, will use default path pattern", file=sys.stderr)
        jsonl_with_paths = None
    
    # 创建输出目录（如果不存在）
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("CSV 转 JSONL 转换工具")
    print("=" * 60)
    print(f"Graph CSV: {graph_csv}")
    print(f"Smiles CSV: {smiles_csv}")
    print(f"输出 JSONL: {output_jsonl}")
    if jsonl_with_paths:
        print(f"图片路径 JSONL: {jsonl_with_paths}")
    print("=" * 60)
    print()
    
    # 执行转换
    convert_csv_to_jsonl(graph_csv, smiles_csv, output_jsonl, jsonl_with_paths)


if __name__ == '__main__':
    main()

