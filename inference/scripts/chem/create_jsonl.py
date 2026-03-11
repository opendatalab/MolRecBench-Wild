#!/usr/bin/env python3
"""
从 CSV 文件构造 JSONL 文件，包含 data_id 和 image_dir_p 两个字段。
"""

import csv
import json
import argparse
import sys
from pathlib import Path


def create_jsonl_from_csv(csv_path, output_jsonl, id_column='id', file_path_column='file_path'):
    """
    从 CSV 文件读取数据，构造 JSONL 文件。
    
    Args:
        csv_path: 输入 CSV 文件路径
        output_jsonl: 输出 JSONL 文件路径
        id_column: CSV 中 ID 列的名称（默认：'id'）
        file_path_column: CSV 中文件路径列的名称（默认：'file_path'）
    """
    records_written = 0
    records_skipped = 0
    
    with open(csv_path, 'r', encoding='utf-8') as csv_file, \
         open(output_jsonl, 'w', encoding='utf-8') as jsonl_file:
        
        reader = csv.DictReader(csv_file)
        
        for row_num, row in enumerate(reader, start=2):  # 从第2行开始（跳过表头）
            # 提取字段
            data_id = row.get(id_column, '').strip()
            image_dir_p = row.get(file_path_column, '').strip()
            
            # 检查必需字段
            if not data_id:
                print(f"Warning: Row {row_num} has empty {id_column}, skipping...", file=sys.stderr)
                records_skipped += 1
                continue
            
            if not image_dir_p:
                print(f"Warning: Row {row_num} has empty {file_path_column}, skipping...", file=sys.stderr)
                records_skipped += 1
                continue
            
            # 构造 JSON 对象
            record = {
                'data_id': data_id,
                'image_dir_p': image_dir_p
            }
            
            # 写入 JSONL
            jsonl_file.write(json.dumps(record, ensure_ascii=False) + '\n')
            records_written += 1
            
            # 每处理 1000 条记录输出一次进度
            if records_written % 1000 == 0:
                print(f"Processed {records_written} records...", file=sys.stderr)
    
    print(f"\n✅ Successfully created {output_jsonl}", file=sys.stderr)
    print(f"   - Records written: {records_written}", file=sys.stderr)
    if records_skipped > 0:
        print(f"   - Records skipped: {records_skipped}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='从 CSV 文件构造 JSONL 文件，包含 data_id 和 image_dir_p 两个字段。'
    )
    parser.add_argument('csv_path', help='输入 CSV 文件路径')
    parser.add_argument('output_jsonl', help='输出 JSONL 文件路径')
    parser.add_argument(
        '--id-column',
        default='id',
        help='CSV 中 ID 列的名称（默认：id）'
    )
    parser.add_argument(
        '--file-path-column',
        default='file_path',
        help='CSV 中文件路径列的名称（默认：file_path）'
    )
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not Path(args.csv_path).exists():
        print(f"Error: Input CSV file '{args.csv_path}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # 创建输出目录（如果不存在）
    output_path = Path(args.output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 执行转换
    create_jsonl_from_csv(
        args.csv_path,
        args.output_jsonl,
        args.id_column,
        args.file_path_column
    )


if __name__ == '__main__':
    main()

